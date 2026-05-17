"""Сервисные функции для работы с книгами."""

from django.db.models.functions import Substr

from django.contrib.auth.models import User

from typing import TypeVar, Callable

from django.core.exceptions import ImproperlyConfigured

from django.db.models.query import RawQuerySet

from opds_catalog.utils import to_int
from constance import config
from django.db.models import QuerySet, Value, CharField, Count
from django.utils.html import strip_tags
from django.utils.translation import gettext as _
from opds_catalog.services import SearchType
from opds_catalog.models import Book, Author
from opds_catalog.opds_paginator import Paginator as OPDS_Paginator


T = TypeVar("T")

SearchFunction = Callable[[bool, str, str | None, User | None], QuerySet[Book]]

DEFAULT_ORDER_BY = ["search_title", "-docdate"]


# Стратегии поиска
def find_by_bookshelf(
    auth_enabled: bool, _: str, __: str | None = None, user: User | None = None
) -> QuerySet[Book]:
    """Книги на книжной полки пользователя."""
    if not auth_enabled:
        raise ImproperlyConfigured(
            f"Attempt to read {user} bookshelf from catalog without authorization"
        )
    return Book.objects.filter(bookshelf__user=user).order_by("-bookshelf_readtime")


def find_by_author_and_series(
    _: bool, author_id: str, series_id: str | None = None, __=None
) -> QuerySet[Book]:
    """Поиск книг по автору и серии."""
    DEFAULT_ORDER_BY.insert(0, "bseries__ser_no")
    return Book.objects.filter(
        author_id=to_int(author_id), series_id=to_int(series_id)
    ).order_by(*DEFAULT_ORDER_BY)


def find_book_doubles(
    _: bool, book_id: str, __: str | None = None, ___=None
) -> QuerySet[Book]:
    """Поиск дубликатов книги."""
    mbook = Book.objects.get(id=book_id)
    return (
        Book.objects.filter(title__iexact=mbook.title, authors__in=mbook.authors.all())
        .exclude(id=book_id)
        .order_by(*DEFAULT_ORDER_BY)
    )


def find_books_by_substring(
    _: bool, term: str, __: str | None = None, ___=None
) -> QuerySet[Book]:
    """Поиск книг по подстроке."""
    return Book.objects.filter(search_title__contains=term.upper()).order_by(
        *DEFAULT_ORDER_BY
    )


def find_books_by_start_letters(
    _: bool, term: str, __: str | None = None, ___=None
) -> QuerySet[Book]:
    """Поиск книг, начинающихся с заданной последовательности символов."""
    return Book.objects.filter(search_title__startswith=term.upper()).order_by(
        *DEFAULT_ORDER_BY
    )


def find_books_by_exact_match(
    _: bool, term: str, __: str | None = None, ___=None
) -> QuerySet[Book]:
    """Поиск книг по названию."""
    return Book.objects.filter(search_title=term.upper()).order_by(*DEFAULT_ORDER_BY)


def find_books_by_author(
    _: bool, author_id: str, __: str | None = None, ___=None
) -> QuerySet[Book]:
    """Поиск книг по автору."""
    return Book.objects.filter(authors=to_int(author_id)).order_by(*DEFAULT_ORDER_BY)


def find_books_by_series(
    _: bool, series_id: str, __: str | None = None, ___=None
) -> QuerySet[Book]:
    """Поиск книг по серии."""
    DEFAULT_ORDER_BY.insert(0, "bseries__ser_no")
    return Book.objects.filter(series=to_int(series_id)).order_by(*DEFAULT_ORDER_BY)


def find_books_by_genre(
    _: bool, genre_id: str, __: str | None = None, ___=None
) -> QuerySet[Book]:
    """Поиск книг по жанру."""
    return Book.objects.filter(genres=to_int(genre_id)).order_by(*DEFAULT_ORDER_BY)


SEARCH_BOOK_REGISTRY: dict[str, SearchFunction] = {
    SearchType.ByUser: find_by_bookshelf,
    SearchType.ByAuthorAndSeries: find_by_author_and_series,
    SearchType.Doubles: find_book_doubles,
    SearchType.BySubstring: find_books_by_substring,
    SearchType.ByStartWith: find_books_by_start_letters,
    SearchType.ByExactMatch: find_books_by_exact_match,
    SearchType.ByAuthor: find_books_by_author,
    SearchType.BySeries: find_books_by_series,
    SearchType.ByGenre: find_books_by_genre,
}


def search_book(
    type: str, term: str, second_term: str | None = None, user=None
) -> QuerySet[Book, Book]:
    """Формирование запроса на выборку книг."""
    search_function = SEARCH_BOOK_REGISTRY.get(type)
    if search_function is None:
        raise ValueError(f"Search type '{type}' is not supported")
    return search_function(config.SOPDS_AUTH, term, second_term, user)


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
    books = (
        Book.objects.filter(search_title__startswith=chars)
        .annotate(
            l=Value(length, output_field=CharField()),
            cid=Substr("search_title", 1, length),
        )
        .values("l", "cid")
        .annotate(cnt=Count("cid"))
        .order_by("cid")
    )
    if lang_code:
        books.filter(lang_code=lang_code)

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
