"""Сервисные функции для работы с книгами."""

from __future__ import annotations

from typing import Callable, TypeVar

from constance import config
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import Paginator
from django.db.models import CharField, Count, Prefetch, QuerySet, Value
from django.db.models.functions import Substr
from django.db.models.query import RawQuerySet
from django.utils.html import strip_tags
from django.utils.translation import gettext as _

from opds_catalog.models import Author, Book, bookshelf
from opds_catalog.services import SearchType
from opds_catalog.utils import get_lang_name, to_int

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
    return Book.objects.filter(
        author_id=to_int(author_id), series_id=to_int(series_id)
    ).order_by(*DEFAULT_ORDER_BY, "bseries__ser_no")


def find_book_doubles(
    _: bool, book_id: str, __: str | None = None, ___=None
) -> QuerySet[Book]:
    """Поиск дубликатов книги."""
    mbook = Book.objects.only("title").get(id=to_int(book_id))
    return (
        Book.objects.filter(title__iexact=mbook.title, authors__in=mbook.authors.all())
        .exclude(id=to_int(book_id))
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
    return Book.objects.filter(series=to_int(series_id)).order_by(
        *DEFAULT_ORDER_BY, "bseries__ser_no"
    )


def find_books_by_genre(
    _: bool, genre_id: str, __: str | None = None, ___=None
) -> QuerySet[Book]:
    """Поиск книг по жанру."""
    return Book.objects.filter(genres=to_int(genre_id)).order_by(*DEFAULT_ORDER_BY)


SEARCH_BOOK_REGISTRY: dict[str, SearchFunction] = {
    SearchType.BY_USER: find_by_bookshelf,
    SearchType.BY_AUTHOR_AND_SERIES: find_by_author_and_series,
    SearchType.DOUBLES: find_book_doubles,
    SearchType.BY_SUBSTRING: find_books_by_substring,
    SearchType.BY_START_WITH: find_books_by_start_letters,
    SearchType.BY_EXACT_MATCH: find_books_by_exact_match,
    SearchType.BY_AUTHOR: find_books_by_author,
    SearchType.BY_SERIES: find_books_by_series,
    SearchType.BY_GENRE: find_books_by_genre,
}


def search_book(
    type: str, term: str, second_term: str | None = None, user=None
) -> QuerySet[Book, Book]:
    """Формирование запроса на выборку книг."""
    search_function = SEARCH_BOOK_REGISTRY.get(type)
    if search_function is None:
        raise ValueError(f"Search type '{type}' is not supported")
    return search_function(config.SOPDS_AUTH, term, second_term, user)


def _build_book_item(row: Book, user=None, auth_enabled=False) -> dict:
    """Преобразует Book в словарь для постраничного вывода.

    Требует prefetch_related:
      - Prefetch('authors', to_attr='c_authors')
      - Prefetch('genres', to_attr='c_genres')
      - Prefetch('series', to_attr='c_series')
      - Prefetch('bseries_set', to_attr='c_ser_no')
    При auth_enabled дополнительно:
      - Prefetch('bookshelf_set', queryset=bookshelf.objects.filter(user=user), to_attr='c_bookshelf')
    """
    authors_list = list(row.c_authors)
    genres_list = list(row.c_genres)
    series_list = list(row.c_series)
    ser_no_list = list(row.c_ser_no)

    readtime = None
    if auth_enabled and hasattr(row, "c_bookshelf") and row.c_bookshelf:
        readtime = row.c_bookshelf[0].readtime

    return {
        "doubles": 0,
        "lang_code": row.lang_code,
        "lang": get_lang_name(row.lang),
        "filename": row.filename,
        "path": row.path,
        "registerdate": row.registerdate,
        "id": row.id,
        "annotation": strip_tags(row.annotation),
        "docdate": row.docdate,
        "format": row.format,
        "title": row.title,
        "filesize": row.filesize,
        "authors": authors_list,
        "genres": genres_list,
        "series": series_list,
        "ser_no": ser_no_list,
        "readtime": readtime,
    }


def _dedup_items(
    items: list[dict],
) -> tuple[list[dict], str, set]:
    """Схлопывает последовательные элементы с одинаковым названием+автором."""
    if not items:
        return [], "", set()

    deduped: list[dict] = []
    prev_title = ""
    prev_authors_set: set[int] = set()

    for p in items:
        title: str = p["title"]
        authors_set: set[int] = {a.id for a in p["authors"]}
        if title.upper() == prev_title.upper() and authors_set == prev_authors_set:
            deduped[-1]["doubles"] += 1
        else:
            deduped.append(p)
        prev_title = title
        prev_authors_set = authors_set

    return deduped, prev_title, prev_authors_set


def _paginator_to_dict(page) -> dict:
    """Преобразует Django Paginator Page в словарь, совместимый с get_data_dict()."""
    paginator = page.paginator
    return {
        "num_pages": paginator.num_pages,
        "has_previous": page.has_previous(),
        "has_next": page.has_next(),
        "previous_page_number": page.previous_page_number()
        if page.has_previous()
        else 1,
        "next_page_number": page.next_page_number()
        if page.has_next()
        else paginator.num_pages,
        "number": page.number,
        "page_range": list(paginator.page_range),
    }


def paginated_book_content(
    books: QuerySet[Book, Book],
    page_num: int,
    search_doubles: bool = False,
    user=None,
    auth_enabled: bool = False,
) -> tuple[list[dict], dict]:
    """Постраничный вывод списка книг.

    :param books: QuerySet книг с применённым search_filter.
    :param page_num: Номер страницы.
    :param search_doubles: Если True — не скрывать дубликаты.
    :param user: Пользователь (нужен для readtime, auth должен быть включен).
    :param auth_enabled: Флаг авторизации.

    :returns: (items, paginator_dict)
    """
    maxitems = config.SOPDS_MAXITEMS

    # Prefetch связанных объектов для устранения N+1
    prefetch = [
        Prefetch("authors", to_attr="c_authors"),
        Prefetch("genres", to_attr="c_genres"),
        Prefetch("series", to_attr="c_series"),
        Prefetch("bseries_set", to_attr="c_ser_no"),
    ]
    if auth_enabled and user is not None:
        prefetch.append(
            Prefetch(
                "bookshelf_set",
                queryset=bookshelf.objects.filter(user=user),
                to_attr="c_bookshelf",
            )
        )
    books = books.prefetch_related(*prefetch)

    django_paginator = Paginator(books, maxitems)
    page = django_paginator.page(page_num)

    summary_DOUBLES_HIDE = config.SOPDS_DOUBLES_HIDE and not search_doubles

    # Собираем элементы страницы
    if summary_DOUBLES_HIDE and page.has_previous():
        # Добавляем последний элемент предыдущей страницы для корректной
        # дедупликации на границе страниц
        prev_page = django_paginator.page(page.previous_page_number())
        page_objects = [prev_page.object_list[len(prev_page.object_list) - 1]] + list(
            page.object_list
        )
    else:
        page_objects = list(page.object_list)

    items = [
        _build_book_item(row, user=user, auth_enabled=auth_enabled)
        for row in page_objects
    ]

    if summary_DOUBLES_HIDE:
        items, prev_title, prev_authors_set = _dedup_items(items)

        # Удаляем граничный элемент с предыдущей страницы
        if page.has_previous() and items:
            items.pop(0)

        # "Вытягиваем" дубликаты со следующей страницы
        if page.has_next() and items:
            next_page = django_paginator.page(page.next_page_number())
            for row in next_page.object_list:
                authors_set = {a.id for a in row.c_authors}
                if (
                    row.title.upper() == prev_title.upper()
                    and authors_set == prev_authors_set
                ):
                    items[-1]["doubles"] += 1
                else:
                    break

    return items, _paginator_to_dict(page)


def book_description(item) -> str:
    """Форматирование описания книги."""
    s = [
        f"<b> {_('Book name:')}</b> {item['title']}<br/>",
    ]
    if item["authors"]:
        # Поддержка как ORM-объектов, так и dict (для тестов)
        if isinstance(item["authors"][0], dict):
            s.append(
                _(
                    "<b>Authors: </b>%s<br/>"
                    % ", ".join(a["full_name"] for a in item["authors"])
                )
            )
        else:
            s.append(
                _(
                    "<b>Authors: </b>%s<br/>"
                    % ", ".join(a.full_name for a in item["authors"])
                )
            )
    if item["genres"]:
        if isinstance(item["genres"][0], dict):
            s.append(
                _(
                    "<b>Genres: </b>%s<br/>"
                    % ", ".join(g["subsection"] for g in item["genres"])
                )
            )
        else:
            s.append(
                _(
                    "<b>Genres: </b>%s<br/>"
                    % ", ".join(g.subsection for g in item["genres"])
                )
            )
    if item["series"]:
        if isinstance(item["series"][0], dict):
            s.append(
                _("<b>Series: </b>%s<br/>")
                % ", ".join(s["ser"] for s in item["series"])
            )
        else:
            s.append(
                _("<b>Series: </b>%s<br/>") % ", ".join(s.ser for s in item["series"])
            )
    if item["ser_no"]:
        if isinstance(item["ser_no"][0], dict):
            s.append(
                _(
                    "<b>No in Series: </b>%s<br/>"
                    % ", ".join(str(s["ser_no"]) for s in item["ser_no"])
                )
            )
        else:
            s.append(
                _(
                    "<b>No in Series: </b>%s<br/>"
                    % ", ".join(str(s.ser_no) for s in item["ser_no"])
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
