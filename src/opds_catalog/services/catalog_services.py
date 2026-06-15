"""Сервисы для работы с каталогами."""

from __future__ import annotations

import logging

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import QuerySet
from django.utils.html import strip_tags

from opds_catalog.models import Book, Catalog

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
    cat: Catalog, current_page: int, pager_max_items: int
) -> tuple[list, dict]:
    """Предоставляет содержимое каталога в виде одной страницы."""
    catalogs_list = get_catalogs_query(cat).order_by("cat_name")
    books_list = get_books_query(cat).order_by("search_title")

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
        merged.append(
            {
                "is_catalog": 0,
                "lang_code": row.lang_code,
                "filename": row.filename,
                "path": row.path,
                "registerdate": row.registerdate,
                "id": row.id,
                "annotation": strip_tags(row.annotation),
                "docdate": row.docdate,
                "format": row.format,
                "title": row.title,
                "filesize": row.filesize // 1000,
                "authors": row.authors.values(),
                "genres": row.genres.values(),
                "series": row.series.values(),
                "ser_no": row.bseries_set.values("ser_no"),
                "prefix": "b",
            }
        )

    paginator = Paginator(merged, pager_max_items)
    try:
        page = paginator.page(current_page)
    except (EmptyPage, PageNotAnInteger):
        page = paginator.page(paginator.num_pages)

    return page.object_list, _paginator_to_dict(page)


def _paginator_to_dict(page) -> dict:
    """Преобразует Django Paginator Page в словарь, совместимый с OPDS."""
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
