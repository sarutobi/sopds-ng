"""Тесты getFileData, getFileDataZip, get_fs_book_path — integration."""

import os
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from opds_catalog.models import Book
from opds_catalog.utils import get_fs_book_path, getFileData, getFileDataZip
from tests.helpers import read_book_from_zip_file, read_file_as_iobytes

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


# ── getFileData ──────────────────────────────────────────────────────────


@pytest.mark.usefixtures("fake_sopds_root_lib")
class TestGetFileData:
    """Тесты getFileData — поиск и чтение файла книги из ФС."""

    def test_read_book_from_regular_file(self, book_factory) -> None:
        from constance import config

        book = book_factory(filename="262001.fb2", cat_type=0, path=".")
        expected = read_file_as_iobytes(
            os.path.join(config.SOPDS_ROOT_LIB, book.filename)
        )
        assert expected is not None

        actual = getFileData(book)
        assert actual is not None
        assert actual.getvalue() == expected.getvalue()

    def test_read_book_from_zip_file(self, book_factory) -> None:
        from constance import config

        book = book_factory(filename="539273.fb2", cat_type=1, path="books.zip")
        expected = read_book_from_zip_file(
            os.path.join(config.SOPDS_ROOT_LIB, book.path), book.filename
        )
        assert expected is not None

        actual = getFileData(book)
        assert actual is not None
        assert actual.getvalue() == expected.getvalue()

    def test_read_book_from_inp_file(self, test_rootlib) -> None:
        expected = read_book_from_zip_file(
            os.path.join(test_rootlib, "books.zip"),
            "539273.fb2",
        )
        assert expected is not None

        book = Book(filename="539273.fb2", cat_type=3, path="inpx/inp/books.zip")
        actual = getFileData(book)
        assert actual is not None
        assert actual.getvalue() == expected.getvalue()

    def test_read_absent_book(self) -> None:
        # Несуще��твующий обычный файл
        book = Book(filename="263001.fb2", cat_type=0, path="data")
        actual = getFileData(book)
        assert actual is None

        # Несуществующий ZIP
        book = Book(filename="539273.fb2", cat_type=1, path="data/books1.zip")
        actual = getFileData(book)
        assert actual is None

        # Несуществующий файл внутри существующего ZIP
        book = Book(filename="559273.fb2", cat_type=1, path="data/books.zip")
        actual = getFileData(book)
        assert actual is None

        # INP — несуществующий архив
        book = Book(filename="539273.fb2", cat_type=3, path="data/inpx/inp/books1.zip")
        actual = getFileData(book)
        assert actual is None

        # INP — несуществующий файл внутри архива
        book = Book(filename="559273.fb2", cat_type=3, path="data/inpx/inp/books.zip")
        actual = getFileData(book)
        assert actual is None


# ── getFileDataZip ───────────────────────────────────────────────────────


@pytest.mark.usefixtures("fake_sopds_root_lib")
class TestGetFileDataZip:
    """Тесты getFileDataZip — упаковка книги в zip-поток."""

    def test_create_zip_stream(self, test_rootlib) -> None:
        expected_file_name = "zip_book.fb2"
        expected_content = read_file_as_iobytes(
            os.path.join(test_rootlib, "262001.fb2")
        )
        book = Book(
            title="zip book",
            format="fb2",
            filename="262001.fb2",
            cat_type=0,
            path=".",
        )

        actual = getFileDataZip(book)
        with zipfile.ZipFile(actual, "r") as tested:
            assert expected_file_name in tested.namelist()
            actual_content = tested.read(expected_file_name)
            assert expected_content.getvalue() == actual_content


# ── get_fs_book_path ─────────────────────────────────────────────────────


@pytest.mark.override_config(SOPDS_ROOT_LIB="opds_catalog/tests/data/")
class TestGetFsBookPath:
    """Тесты get_fs_book_path — формирование пути в ФС."""

    def test_inp_book_path(self) -> None:
        book = Book(filename="539273.fb2", cat_type=3, path="inpx/inp/books.zip")
        expected_path = "opds_catalog/tests/data/books.zip"
        actual_path = get_fs_book_path(book)
        assert actual_path == expected_path

    def test_normal_book_path(self) -> None:
        book = Book(filename="539273.fb2", cat_type=0, path="books.zip")
        expected_path = "opds_catalog/tests/data/books.zip"
        actual_path = get_fs_book_path(book)
        assert actual_path is not None
        assert actual_path == expected_path
