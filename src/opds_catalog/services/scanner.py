"""Сервисы для процесса сканирования библиотеки."""

import logging
import os
from typing import Any

from opds_catalog.constants import CAT_NORMAL
from opds_catalog.models import (
    SIZE_BOOK_FILENAME,
    SIZE_BOOK_PATH,
    SIZE_CAT_CATNAME,
    SIZE_CAT_PATH,
    Book,
    Catalog,
)
from opds_catalog.services.book_writer import (
    BookWriter,
)
from opds_catalog.utils import safe_log_str

scan_logger = logging.getLogger("scanner")

# Default writer for legacy API support
_default_writer = BookWriter(logger=scan_logger)


def findcat(cat_name: str) -> Catalog | None:
    """Поиск каталога по его имени в базе данных."""
    (head, tail) = os.path.split(cat_name)
    try:
        return Catalog.objects.get(
            cat_name=tail[:SIZE_CAT_CATNAME], path=cat_name[:SIZE_CAT_PATH]
        )
    except Catalog.DoesNotExist:
        return None


def addcattree(cat_name: str, archive: int = CAT_NORMAL, size: int = 0) -> Catalog:
    """Рекурсивное создание дерева каталогов."""
    catalog = findcat(cat_name)
    if catalog:
        return catalog
    if cat_name in ("", "."):
        return Catalog.objects.get_or_create(
            parent=None, cat_name=".", path=".", cat_type=CAT_NORMAL
        )[0]
    (head, tail) = os.path.split(cat_name)
    parent = addcattree(head)
    return Catalog.objects.create(
        parent=parent,
        cat_name=tail[:SIZE_CAT_CATNAME],
        path=cat_name[:SIZE_CAT_PATH],
        cat_type=archive,
        cat_size=size,
    )


def findbook(name: str, path: str, setavail: int = 0) -> Book | None:
    """Поиск книги в БД по имени и пути."""
    scan_logger.info(f"Checking book {safe_log_str(name)} metadata in database")
    scan_logger.debug(f"Book path = {safe_log_str(path)}")
    try:
        book = Book.objects.get(
            filename=name[:SIZE_BOOK_FILENAME], path=path[:SIZE_BOOK_PATH]
        )
    except Book.DoesNotExist:
        scan_logger.info("Book not found in database")
        return None

    if setavail:
        scan_logger.info("Updating book availability in database")
        book.avail = 2
        book.save()

    return book


def archive_skip(arcpath: str, arcsize: int, depth: int = 0) -> int:
    """
    Унифицированная проверка: изменялся ли архив.
    depth=0: ZIP (Book.path)
    depth=1: INP (Book.catalog__parent)
    depth=2: INPX (Book.catalog__parent__parent)
    """
    catalog = findcat(arcpath)
    if catalog is None or arcsize != catalog.cat_size:
        return 0

    filter_kwargs: dict[str, Any] = {}
    if depth == 0:
        filter_kwargs = {"path": arcpath}
    elif depth == 1:
        filter_kwargs = {"catalog__parent": catalog}
    elif depth == 2:
        filter_kwargs = {"catalog__parent__parent": catalog}

    return Book.objects.filter(**filter_kwargs).update(avail=2)


def avail_check_prepare():
    """Подготовка признака наличия книг перед сканированием."""
    Book.objects.exclude(avail=0).update(avail=1)


def books_del_phisical():
    """Физическое удаление книг с avail <= 1."""
    return Book.objects.filter(avail__lte=1).delete()
