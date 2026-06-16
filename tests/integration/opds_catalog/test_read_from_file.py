"""Тесты чтения книг из файловой системы — integration, с fake_sopds_root_lib."""

import os

import pytest

from opds_catalog.utils import (
    get_fs_book_path,
    read_from_regular_file,
    read_from_zipped_file,
)
from tests.helpers import read_book_from_zip_file, read_file_as_iobytes

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


# ── Чтение из обычных файлов ────────────────────────────────────────────


@pytest.fixture
def regular_book(book_factory):
    """Создаёт Book-объект для обычного (неархивного) файла."""
    return book_factory(filename="262001.fb2", cat_type=0, path=".")


@pytest.mark.usefixtures("fake_sopds_root_lib")
class TestReadFromRegularFile:
    """Тесты read_from_regular_file."""

    def test_read_book_from_regular_file(self, regular_book) -> None:
        from constance import config

        expected = read_file_as_iobytes(
            os.path.join(config.SOPDS_ROOT_LIB, regular_book.filename)
        )
        assert expected is not None

        actual = read_from_regular_file(
            os.path.join(get_fs_book_path(regular_book), regular_book.filename)
        )
        assert actual is not None
        assert actual.getvalue() == expected.getvalue()

    def test_read_from_unexistent_file(self, book_factory) -> None:
        book = book_factory(filename="263001.fb2", cat_type=0, path=".")
        actual = read_from_regular_file(
            os.path.join(get_fs_book_path(book), book.filename)
        )
        assert actual is None


# ── Чтение из ZIP-архивов ────────────────────────────────────────────────


@pytest.fixture
def zipped_book(book_factory):
    """Создаёт Book-объект для книги внутри ZIP-архива."""
    return book_factory(filename="539273.fb2", cat_type=1, path="books.zip")


@pytest.mark.usefixtures("fake_sopds_root_lib")
class TestReadFromZippedFile:
    """Тесты read_from_zipped_file."""

    def test_read_book_from_zip_file(self, zipped_book) -> None:
        from constance import config

        expected = read_book_from_zip_file(
            os.path.join(config.SOPDS_ROOT_LIB, zipped_book.path),
            zipped_book.filename,
        )
        assert expected is not None

        actual = read_from_zipped_file(
            os.path.join(config.SOPDS_ROOT_LIB, zipped_book.path),
            zipped_book.filename,
        )
        assert actual is not None
        assert actual.getvalue() == expected.getvalue()

    def test_no_book_in_zip_file(self, book_factory) -> None:
        from constance import config

        book = book_factory(filename="559273.fb2", cat_type=1, path="books.zip")

        actual = read_from_zipped_file(
            os.path.join(config.SOPDS_ROOT_LIB, book.path), book.filename
        )
        assert actual is None

    def test_read_book_from_non_existent_zip_file(self, book_factory) -> None:
        from constance import config

        book = book_factory(filename="559273.fb2", cat_type=1, path="books1.zip")

        actual = read_from_zipped_file(
            os.path.join(config.SOPDS_ROOT_LIB, book.path), book.filename
        )
        assert actual is None
