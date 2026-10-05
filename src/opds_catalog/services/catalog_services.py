"""Сервисы для работы с каталогами."""

from __future__ import annotations

import logging

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Prefetch, QuerySet

from opds_catalog.models import Book, Catalog, bookshelf
from opds_catalog.services import book_services
from opds_catalog.services.pagination_utils import paginator_to_dict

DUMMY_CATALOG = Catalog(id=0, cat_name="Empty", cat_type=0)

log = logging.getLogger(__name__)


def get_root() -> Catalog:
    """Возвращает корневой каталог."""
    try:
        cat = Catalog.objects.get(parent__id=None)
        return cat
    except Exception as e:
        log.warning(e)
    return DUMMY_CATALOG


def get_by_id(id: int) -> Catalog:
    """Возвращает каталог по идентификатору.

    :param id: Идентификатор каталога
    :type id: int

    :returns: Найденный каталог или каталог-заглушку если каталога с таким идентификатором
    не существует
    :rtype: Catalog
    """
    try:
        return Catalog.objects.get(id=id)
    except Catalog.DoesNotExist:
        log.error(f"Catalog with id={id} does not exists")
        return DUMMY_CATALOG


def get_catalogs_query(root: Catalog | None) -> QuerySet[Catalog, Catalog]:
    """Запрос подкаталогов текущего каталога.

    :param root: каталог, для которого требуется найти подкаталоги
    :type root: Catalog|None

    :returns: Запрос, позволяющий получить подкаталоги
    :rtype: QuerySet[Catalog, Catalog]
    """
    return Catalog.objects.filter(parent=root)


def get_books_query(catalog: Catalog) -> QuerySet[Book, Book]:
    """Запрос книг в каталоге.

    :param catalog: каталог, в котором требуется найти книги
    :type catalog: Catalog

    :returns: Запрос, позволяющий получить книги
    :rtype: Queryset[Book, Book]
    """
    return Book.objects.filter(catalog=catalog)


def get_catalogs_count(root: Catalog) -> int:
    """Запрос числа подкаталогов в каталоге."""
    return get_catalogs_query(root).count()


def get_books_count(root: Catalog) -> int:
    """Запрос числа книг в каталоге."""
    return get_books_query(root).count()


def paginated_catalog_content(
    cat: Catalog,
    current_page: int,
    pager_max_items: int,
    user=None,
    auth_enabled: bool = False,
) -> tuple[list, dict]:
    """Предоставляет содержимое каталога в виде одной страницы."""

    # Prefetch связанных объектов для книг
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

    catalogs_list = get_catalogs_query(cat).order_by("cat_name")
    books_list = (
        get_books_query(cat).order_by("search_title").prefetch_related(*prefetch)
    )

    # Собираем единый список: сначала подкаталоги, потом книги
    merged: list[dict] = []

    for row in catalogs_list:
        merged.append(
            {
                "is_catalog": 1,
                "title": row.cat_name,
                "id": row.id,
                "cat_type": row.cat_type,
                "parent_id": row.parent_id,
                "prefix": "c",
            }
        )

    for row in books_list:
        item = book_services._build_book_item(row, user, auth_enabled)
        item["is_catalog"] = 0
        item["prefix"] = "b"
        item["filesize"] = item["filesize"] // 1000
        merged.append(item)

    paginator = Paginator(merged, pager_max_items)
    try:
        page = paginator.page(current_page)
    except (EmptyPage, PageNotAnInteger):
        page = paginator.page(paginator.num_pages)

    return page.object_list, paginator_to_dict(page)
