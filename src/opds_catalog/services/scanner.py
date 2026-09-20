"""Сервисы для процесса сканирования библиотеки."""

import logging
import os
from typing import Any

from django.db import transaction

from opds_catalog.constants import CAT_INP, CAT_INPX, CAT_NORMAL, CAT_ZIP
from opds_catalog.models import (
    SIZE_AUTHOR_NAME,
    SIZE_BOOK_ANNOTATION,
    SIZE_BOOK_DOCDATE,
    SIZE_BOOK_FILENAME,
    SIZE_BOOK_FORMAT,
    SIZE_BOOK_LANG,
    SIZE_BOOK_PATH,
    SIZE_BOOK_TITLE,
    SIZE_CAT_CATNAME,
    SIZE_CAT_PATH,
    SIZE_GENRE,
    SIZE_GENRE_SUBSECTION,
    SIZE_SERIES,
    SOPDS_LANG_CODE_OTHER,
    Author,
    Book,
    Catalog,
    Genre,
    LangCodes,
    Series,
    bauthor,
    bgenre,
    bseries,
)
from opds_catalog.utils import getlangcode, p

scan_logger = logging.getLogger("scanner")


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
    scan_logger.info(f"Checking book {name} metadata in database")
    scan_logger.debug(f"Book path = {path}")
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


def addbook(
    name, path, cat, exten, title, annotation, docdate, lang, size=0, archive=0
) -> Book:
    """Добавление книги в коллекцию."""
    return Book.objects.create(
        filename=name[:SIZE_BOOK_FILENAME],
        path=path[:SIZE_BOOK_PATH],
        catalog=cat,
        filesize=size,
        format=exten.lower()[:SIZE_BOOK_FORMAT],
        title=title[:SIZE_BOOK_TITLE],
        search_title=title.upper()[:SIZE_BOOK_TITLE],
        annotation=p(annotation, SIZE_BOOK_ANNOTATION),
        docdate=docdate[:SIZE_BOOK_DOCDATE],
        lang=lang[:SIZE_BOOK_LANG],
        cat_type=archive,
        avail=2,
        lang_code=getlangcode(title),
    )


def addauthor(full_name: str) -> Author:
    """Создание или получение автора."""
    author, _ = Author.objects.get_or_create(
        full_name=full_name[:SIZE_AUTHOR_NAME],
        defaults={
            "search_full_name": full_name.upper()[:SIZE_AUTHOR_NAME],
            "lang_code": getlangcode(full_name),
        },
    )
    return author


def findauthor(full_name: str) -> list[Author]:
    """Поиск автора по полному имени."""
    return list(Author.objects.filter(full_name=full_name[:SIZE_AUTHOR_NAME]))[:1]


def addbauthor(book: Book, author: Author):
    """Связь книги с автором."""
    bauthor.objects.get_or_create(book=book, author=author)


def addgenre(genre: str) -> Genre:
    """Создание или получение жанра."""
    # Здесь 'Unknown genre' захардкожен или должен быть из locale/constants
    # Для совместимости с оригиналом используем заглушку или перенесем в constants
    genre_obj, _ = Genre.objects.get_or_create(
        genre=genre[:SIZE_GENRE],
        defaults={
            "section": "Unknown genre",
            "subsection": genre[:SIZE_GENRE_SUBSECTION],
        },
    )
    return genre_obj


def addbgenre(book: Book, genre: Genre):
    """Связь книги с жанром."""
    bgenre.objects.get_or_create(book=book, genre=genre)


def addseries(ser: str) -> Series:
    """Создание или получение серии."""
    series, _ = Series.objects.get_or_create(
        ser=ser[:SIZE_SERIES],
        defaults={
            "search_ser": ser.upper()[:SIZE_SERIES],
            "lang_code": getlangcode(ser),
        },
    )
    return series


def addbseries(book: Book, ser: Series, ser_no: int):
    """Связь книги с серией."""
    bseries.objects.get_or_create(book=book, ser=ser, ser_no=ser_no)


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
