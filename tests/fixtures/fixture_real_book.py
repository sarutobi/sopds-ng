"""Фикстуры для книг, размещенных в файловой системе"""

from typing import Callable

import os
from io import BytesIO

import pytest


@pytest.fixture(scope="session")
def simple_fb2() -> str:
    """Имя файла обычной FB2 книги"""
    return "262001.fb2"


@pytest.fixture(scope="session")
def zipped_fb2() -> str:
    """Имя файла FB2 книги, сжатой ZIP"""
    return "262001.zip"


@pytest.fixture(scope="session")
def bad_fb2() -> str:
    """Имя файла с некорректной книгой в формате FB2"""
    return "badfile.fb2"


@pytest.fixture(scope="session")
def epub_book() -> str:
    """Имя файла книги в формате epub"""
    return "mirer.epub"


@pytest.fixture(scope="session")
def mobi_book() -> str:
    """Имя книги в формате .mobi"""
    return "robin_cook.mobi"


@pytest.fixture(scope="session")
def obsolete_fb2_zip() -> str:
    """Имя файла ZIP архива, кодировка имен файлов в которм отличается от UTF-8"""
    return "wrong_encoded.zip"


@pytest.fixture(scope="session")
def get_file_content(test_rootlib) -> Callable:
    """Возвращает функцию, считывающую файл из файловой системы"""

    def read_file(filename: str) -> BytesIO:
        fname = os.path.join(test_rootlib, filename)
        with open(fname, "rb") as f:
            content = BytesIO(f.read())

        content.seek(0)
        return content

    return read_file


@pytest.fixture(scope="module")
def fb2_book_from_fs(get_file_content, simple_fb2) -> BytesIO:
    """Предоставляет считанную из ФС книгу в формате FB2"""
    return get_file_content(simple_fb2)


@pytest.fixture(scope="module")
def zipped_fb2_book_from_fs(get_file_content, zipped_fb2) -> BytesIO:
    """Предоставляет считанную из ФС книгу в формате FB2, сжатую zip"""
    return get_file_content(zipped_fb2)


@pytest.fixture(scope="module")
def epub_book_from_fs(get_file_content, epub_book) -> BytesIO:
    """Предоставляет считанную из ФС книгу в формате EPUB"""
    return get_file_content(epub_book)


@pytest.fixture(scope="module")
def mobi_book_from_fs(get_file_content, mobi_book) -> BytesIO:
    """Предоставляет считанную из ФС книгу в формате EPUB"""
    return get_file_content(mobi_book)


@pytest.fixture(scope="module")
def wrong_encoded_fb2_zip(get_file_content, obsolete_fb2_zip) -> BytesIO:
    """Предоставляет книгу с кодировкой названия в cp866"""
    return get_file_content(obsolete_fb2_zip)


# @pytest.fixture
# def iterate_books(
#     fb2_book_from_fs, zipped_fb2_book_from_fs, epub_book_from_fs, mobi_book_from_fs
# ):
#     """Предоставляет различные типы книг"""
#     list = [
#         fb2_book_from_fs,
#         zipped_fb2_book_from_fs,
#         epub_book_from_fs,
#         mobi_book_from_fs,
#     ]
#     for book in list:
#         yield book


@pytest.fixture
def book_from_fs(get_file_content, request) -> BytesIO:
    """Обобщенная фикстура для предоставления запрошенной книги из ФС"""
    return get_file_content(request.param)
