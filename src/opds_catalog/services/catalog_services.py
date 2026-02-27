"""Сервисы для работы с каталогами."""

# from ty_extensions import Unknown

from django.db.models import QuerySet
from django.utils.html import strip_tags

from opds_catalog.models import Book, Catalog
from opds_catalog.opds_paginator import Paginator as OPDS_Paginator


def get_root() -> Catalog:
    """Возвращает корневой каталог."""
    return Catalog.objects.get(parent__id=None)


def get_by_id(id: int) -> Catalog | None:
    """Возвращает каталог по идентификатору.

    :param id: Идентификатор каталога
    :type id: int

    :returns: Найденный каталог или None если каталога с таким идентификатором
    не существует
    :rtype: Catalog | None
    """
    try:
        return Catalog.objects.get(id=id)
    except Catalog.DoesNotExist:
        return None


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
    catalogs_count = catalogs_list.count()
    # prefetch_related on sqlite on items >999 therow error "too many SQL variables"
    books_list = get_books_query(cat).order_by("search_title")
    books_count = books_list.count()

    # Получаем результирующий список
    op = OPDS_Paginator(catalogs_count, books_count, current_page, pager_max_items)
    items = []

    for row in catalogs_list[op.d1_first_pos : op.d1_last_pos + 1]:
        p = {
            "is_catalog": 1,
            "title": row.cat_name,
            "id": row.id,  # ty: ignore [unresolved-attribute]
            "cat_type": row.cat_type,
            "parent_id": row.parent_id,  # ty: ignore [unresolved-attribute]
        }
        items.append(p)

    for row in books_list[op.d2_first_pos : op.d2_last_pos + 1]:
        p = {
            "is_catalog": 0,
            "lang_code": row.lang_code,
            "filename": row.filename,
            "path": row.path,
            "registerdate": row.registerdate,
            "id": row.id,  # ty: ignore [unresolved-attribute]
            "annotation": strip_tags(row.annotation),
            "docdate": row.docdate,
            "format": row.format,
            "title": row.title,
            "filesize": row.filesize // 1000,
            "authors": row.authors.values(),
            "genres": row.genres.values(),
            "series": row.series.values(),
            "ser_no": row.bseries_set.values("ser_no"),  # ty: ignore [unresolved-attribute]
        }
        items.append(p)

    return items, op.get_data_dict()
