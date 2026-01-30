"""Фикстуры для книг, размещенных в файловой системе"""

import os
from io import BytesIO

import pytest

from tests.opds_catalog.helpers import read_file_as_iobytes


@pytest.fixture
def fb2_book_from_fs(test_rootlib) -> BytesIO:
    """Предоставляет считанную из ФС книгу в формате FB2"""
    return read_file_as_iobytes(os.path.join(test_rootlib, "262001.fb2"))


@pytest.fixture(scope="module")
def zipped_fb2_book_from_fs(test_rootlib) -> BytesIO:
    """Предоставляет считанную из ФС книгу в формате FB2, сжатую zip"""
    return read_file_as_iobytes(os.path.join(test_rootlib, "262001.zip"))


@pytest.fixture(scope="module")
def epub_book_from_fs(test_rootlib) -> BytesIO:
    """Предоставляет считанную из ФС книгу в формате EPUB"""
    return read_file_as_iobytes(os.path.join(test_rootlib, "mirer.epub"))


@pytest.fixture
def mobi_book_from_fs(test_rootlib) -> BytesIO:
    """Предоставляет считанную из ФС книгу в формате EPUB"""
    return read_file_as_iobytes(os.path.join(test_rootlib, "robin_cook.mobi"))


@pytest.fixture
def wrong_encoded_fb2_zip(test_rootlib) -> BytesIO:
    """Предоставляет книгу с кодировкой названия в cp866"""
    return read_file_as_iobytes(os.path.join(test_rootlib, "wrong_encoded.zip"))


@pytest.fixture
def iterate_books(
    fb2_book_from_fs, zipped_fb2_book_from_fs, epub_book_from_fs, mobi_book_from_fs
):
    """Предоставляет различные типы книг"""
    list = [
        fb2_book_from_fs,
        zipped_fb2_book_from_fs,
        epub_book_from_fs,
        mobi_book_from_fs,
    ]
    for book in list:
        yield book


@pytest.fixture
def book_from_fs(test_rootlib, request) -> BytesIO:
    """Обобщенная фикстура для предоставления запрошенной книги из ФС"""
    return read_file_as_iobytes(os.path.join(test_rootlib, request.param))
