from io import BytesIO

import pytest

from book_tools.format.fb2 import (
    FB2,
)
from book_tools.mime_detector import (
    EPUBContentValidator,
    FB2ContentValidator,
    FB2ZipContentValidator,
    MobiContentValidator,
)
from book_tools.services import (
    create_bookfile_service,
)


def test_fb2_metadata_service_returns_the_same(fb2_book_from_fs) -> None:
    """Тест сервиса метаданных книги в формате fb2"""
    actual = create_bookfile_service(fb2_book_from_fs, "Test Book")
    expected = FB2(fb2_book_from_fs, "Test Book")
    assert actual == expected


def test_fb2_metadata_service_returns_the_same_zipped(
    fb2_book_from_fs, zipped_fb2_book_from_fs
) -> None:
    """Тест сервиса метаданных книги в формате FB2, сжатой zip"""
    actual = create_bookfile_service(zipped_fb2_book_from_fs, "Test book")
    expected = create_bookfile_service(fb2_book_from_fs, "Test book")
    assert actual == expected


@pytest.mark.parametrize(
    "fname, expected", [("test.fb2", True), ("test.xml", True), ("test.zip", True)]
)
def test_fb2_content_validator(fname, fb2_book_from_fs, expected) -> None:
    validator = FB2ContentValidator()
    assert validator.is_valid(fb2_book_from_fs) == expected


def test_fb2zip_content_validator(zipped_fb2_book_from_fs) -> None:
    validator = FB2ZipContentValidator()
    assert validator.is_valid(zipped_fb2_book_from_fs)


@pytest.mark.parametrize(
    "book_from_fs",
    [
        "epub_book",
    ],
    indirect=True,
)
def test_epub_content_validator(book_from_fs) -> None:
    """Тест определения типа EPUB"""
    validator = EPUBContentValidator()
    assert validator.is_valid(book_from_fs)


@pytest.mark.parametrize(
    "book_from_fs",
    [
        "mobi_book",
    ],
    indirect=True,
)
def test_mobi_content_validator(book_from_fs) -> None:
    validator = MobiContentValidator()
    assert validator.is_valid(book_from_fs)
