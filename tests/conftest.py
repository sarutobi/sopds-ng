"""Общие фикстуры для всего проекта"""

import os
from pathlib import Path
import pytest
from tests.opds_catalog.helpers import read_file_as_iobytes
import io


@pytest.fixture
def fake_sopds_root_lib(override_config, test_rootlib):
    """Корневая директория библиотеки для тестов"""
    with override_config(SOPDS_ROOT_LIB=test_rootlib):
        yield


@pytest.fixture
def test_rootlib() -> str:
    """Корневая директория библиотеки для тестов"""
    test_module_path: str = os.path.dirname(Path(__file__).resolve())
    test_ROOTLIB = os.path.join(test_module_path, "opds_catalog/data")
    return test_ROOTLIB


@pytest.fixture
def fb2_book_from_fs(test_rootlib) -> io.BytesIO:
    """Предоставляет считанную из ФС книгу в формате FB2"""
    return read_file_as_iobytes(os.path.join(test_rootlib, "262001.fb2"))


@pytest.fixture
def zipped_fb2_book_from_fs(test_rootlib) -> io.BytesIO:
    """Предоставляет считанную из ФС книгу в формате FB2, сжатую zip"""
    return read_file_as_iobytes(os.path.join(test_rootlib, "262001.zip"))


@pytest.fixture
def epub_book_from_fs(test_rootlib) -> io.BytesIO:
    """Предоставляет считанную из ФС книгу в формате EPUB"""
    return read_file_as_iobytes(os.path.join(test_rootlib, "mirer.epub"))


@pytest.fixture
def mobi_book_from_fs(test_rootlib) -> io.BytesIO:
    """Предоставляет считанную из ФС книгу в формате EPUB"""
    return read_file_as_iobytes(os.path.join(test_rootlib, "robin_cook.mobi"))


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
