"""Сервисные функции для работы с книгами."""

from django.db.models.query import RawQuerySet

from dataclasses import dataclass
from typing import Any

from constance import config
from django.db.models import Q, QuerySet
from django.utils.html import strip_tags
from django.utils.translation import gettext as _

from opds_catalog.models import Book, Author
from opds_catalog.opds_paginator import Paginator as OPDS_Paginator


@dataclass
class OPDSSearchType:
    """Возможные варианты поиска книг в каталоге."""

    BySubstring = "m"
    ByStartWith = "b"
    ByExact = "e"
    ByAuthor = "a"
    BySeries = "s"
    ByAuthorAndSeries = "as"
    ByGenre = "g"
    ByUser = "u"
    Doubles = "d"


def _to_int(val: Any, default: int = 0) -> int:
    try:
        result = int(val)
        return result
    except Exception:
        return default


def find_by_title_contains(filter: str) -> Q:
    """Поиск книг по названию, содержащему подстроку."""
    return Q(search_title__contains=filter.upper())


def find_by_title_startswith(filter: str) -> Q:
    """Поиск книг по названию, начинающемуся на подстроку."""
    return Q(search_title__startswith=filter.upper())


def find_by_title(filter: str) -> Q:
    """Поиск книги по названию."""
    return Q(search_title=filter.upper())


def find_by_author(filter: str) -> Q:
    """Поиск книги по автору."""
    return Q(authors=_to_int(filter))


def find_by_series(filter: str) -> Q:
    """Поиск книг по серии."""
    return Q(series=_to_int(filter))


def find_by_genre(filter: str) -> Q:
    """Поиск книг по жанру."""
    return Q(genres=_to_int(filter))


def find_by_bookshelf(filter) -> Q:
    """Поиск книг на полке пользователя."""
    return Q(bookshelf__user=filter)


def find_book_doubles(book_id: int) -> QuerySet[Book, Book]:
    """Поиск дубликатов книги."""
    mbook = Book.objects.get(id=book_id)
    return Book.objects.filter(
        title__iexact=mbook.title, authors__in=mbook.authors.all()
    ).exclude(id=book_id)


def _order_by(type: str) -> list[str]:
    order_by: list[str] = ["search_title", "-docdate"]

    if type == OPDSSearchType.ByUser:
        order_by = [
            "-bookshelf__readtime",
        ]
    elif type in (OPDSSearchType.BySeries, OPDSSearchType.ByAuthorAndSeries):
        order_by.insert(0, "bseries__ser_no")
    return order_by


def search_book(
    type: str, term: str, second_term: str, user=None
) -> QuerySet[Book, Book]:
    """Формирование запроса на выборку книг."""
    queries = {
        OPDSSearchType.BySubstring: find_by_title_contains,
        OPDSSearchType.ByStartWith: find_by_title_startswith,
        OPDSSearchType.ByExact: find_by_title,
        OPDSSearchType.ByAuthor: find_by_author,
        OPDSSearchType.BySeries: find_by_series,
        OPDSSearchType.ByGenre: find_by_genre,
    }
    order_by: list[str] = _order_by(type)

    if type == OPDSSearchType.Doubles:
        return find_book_doubles(_to_int(term))

    if type == OPDSSearchType.ByUser:
        if config.SOPDS_AUTH:
            filter = find_by_bookshelf(user)
        else:
            filter = Q(id=0)

    elif type == OPDSSearchType.ByAuthorAndSeries:
        filter = Q(
            find_by_author(term),
            find_by_series(second_term),
        )
    else:
        filter: Q = queries.get(type)(term)  # ty: ignore

    return Book.objects.filter(filter).order_by(*order_by)


def paginated_book_content(
    books: QuerySet[Book, Book], page_num: int, search_doubles: bool = False
):
    """Постраничный вывод списка книг."""
    books_count = books.count()
    op = OPDS_Paginator(books_count, 0, page_num, config.SOPDS_MAXITEMS)
    items = []

    prev_title = ""
    prev_authors_set = set()

    # Начинаем анализ с последнего элемента на предидущей странице, чторбы он "вытянул"
    # с этой страницы свои дубликаты если они есть
    summary_DOUBLES_HIDE = config.SOPDS_DOUBLES_HIDE and not search_doubles
    start = (
        op.d1_first_pos
        if ((op.d1_first_pos == 0) or (not summary_DOUBLES_HIDE))
        else op.d1_first_pos - 1
    )
    finish = op.d1_last_pos

    for row in books[start : finish + 1]:
        p = {
            "doubles": 0,
            "lang_code": row.lang_code,
            "filename": row.filename,
            "path": row.path,
            "registerdate": row.registerdate,
            "id": row.id,  # # ty: ignore[unresolved-attribute]
            "annotation": strip_tags(row.annotation),
            "docdate": row.docdate,
            "format": row.format,
            "title": row.title,
            "filesize": row.filesize // 1000,
            "authors": row.authors.values(),
            "genres": row.genres.values(),
            "series": row.series.values(),
            "ser_no": row.bseries_set.values("ser_no"),  # ty: ignore[unresolved-attribute]
        }
        if summary_DOUBLES_HIDE:
            title: str = p["title"]
            authors_set: set[int] = {a["id"] for a in p["authors"]}
            if title.upper() == prev_title.upper() and authors_set == prev_authors_set:
                items[-1]["doubles"] += 1
            else:
                items.append(p)
            prev_title = title
            prev_authors_set = authors_set
        else:
            items.append(p)

    # "вытягиваем" дубликаты книг со следующей страницы и удаляем первый элемент
    # который с предыдущей страницы и "вытягивал" дубликаты с текущей
    if summary_DOUBLES_HIDE:
        double_flag = True
        while ((finish + 1) < books_count) and double_flag:
            finish += 1
            if (
                books[finish].title.upper() == prev_title.upper()
                and {a["id"] for a in books[finish].authors.values()}
                == prev_authors_set
            ):
                items[-1]["doubles"] += 1
            else:
                double_flag = False

        if op.d1_first_pos != 0:
            items.pop(0)

    return items, op


def book_description(item) -> str:
    """Форматирование описания книги."""
    s = [
        f"<b> {_('Book name:')}</b> {item['title']}<br/>",
    ]
    if item["authors"]:
        s.append(
            _(
                "<b>Authors: </b>%s<br/>"
                % ", ".join(a["full_name"] for a in item["authors"])
            )
        )
    if item["genres"]:
        s.append(
            _(
                "<b>Genres: </b>%s<br/>"
                % ", ".join(g["subsection"] for g in item["genres"])
            )
        )
    if item["series"]:
        s.append(
            _("<b>Series: </b>%s<br/>") % ", ".join(s["ser"] for s in item["series"])
        )
    if item["ser_no"]:
        s.append(
            _(
                "<b>No in Series: </b>%s<br/>"
                % ", ".join(str(s["ser_no"]) for s in item["ser_no"])
            )
        )
    s.append(
        _(
            f"<b>File: </b>{item['filename']}<br/><b>File size: </b>{item['filesize']}<br/><b>Changes date: </b>{item['docdate']}<br/>"
        )
    )
    s.append(f"<p class='book'>{item['annotation']}</p>")
    return "".join(s)


def find_books_by_template(
    chars: str, length: int, lang_code: int | None = None
) -> RawQuerySet:
    """Поиск книг по шаблону."""
    if lang_code:
        sql = """select %(length)s as l, substring(search_title,1,%(length)s) as id, count(*) as cnt 
                from opds_catalog_book 
                where lang_code=%(lang_code)s and search_title like '%(chars)s%%%%'
                group by substring(search_title,1,%(length)s)
                order by id""" % {
            "length": length,
            "lang_code": lang_code,
            "chars": chars,
        }
    else:
        sql = """select %(length)s as l, substring(search_title,1,%(length)s) as id, count(*) as cnt 
                from opds_catalog_book 
                where search_title like '%(chars)s%%%%'
                group by substring(search_title,1,%(length)s)
                order by id""" % {"length": length, "chars": chars}

    dataset = Book.objects.raw(sql)
    return dataset


def author_books_count(author: Author | int) -> int:
    """Подсчет числа книг для автора."""
    return Book.objects.filter(authors=author).count()
