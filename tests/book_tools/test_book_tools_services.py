from book_tools.format.mimetype import Mimetype
import pytest

from io import BytesIO
from book_tools.services import (
    create_bookfile_service,
    GenericMimeValidator,
    FB2MimeValidator,
    FB2ZipMimeValidator,
    EPUBMimeValidator,
    MobiMimeValidator,
    detect_mime_service,
)

from book_tools.format.fb2 import (
    FB2,
)


# fb2_books_to_try = (
#     (fb2_book_fabric(title="Good Book"), nullcontext()),
#     (
#         fb2_book_fabric(title="Bad Book", correct=False),
#         pytest.raises(FB2StructureException),
#     ),
# )
#
#
# @pytest.mark.parametrize(
#     "book, expected_exception", fb2_books_to_try, ids=("Good file", "Bad file")
# )
# def test_extract_fb2_metadata_service(book, expected_exception) -> None:
#     file = BytesIO(book)
#     with expected_exception:
#         book_actual = extract_fb2_metadata_service(file, "Test Book")
#         assert book_actual is not None


def test_book_parsing(virtual_fb2_book) -> None:
    result = create_bookfile_service(virtual_fb2_book, "Test Book")
    assert result is not None


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


def test_genericmimevalidator() -> None:
    validator = GenericMimeValidator()
    assert validator is not None
    assert validator.is_valid("test.txt", BytesIO())


@pytest.mark.parametrize(
    "fname, expected", [("test.fb2", True), ("test.xml", True), ("test.zip", True)]
)
def test_fb2_mimevalidator(fname, fb2_book_from_fs, expected) -> None:
    validator = FB2MimeValidator()
    assert validator.is_valid(fname, fb2_book_from_fs) == expected


def test_fb2zip_mimevalidator(zipped_fb2_book_from_fs) -> None:
    validator = FB2ZipMimeValidator()
    assert validator.is_valid("test_zip.fb2", zipped_fb2_book_from_fs)


def test_epub_mimevalidator(epub_book_from_fs) -> None:
    """Тест определения типа EPUB"""
    validator = EPUBMimeValidator()
    assert validator.is_valid("test.epub", epub_book_from_fs)


def test_mobi_mimevalidator(mobi_book_from_fs) -> None:
    validator = MobiMimeValidator()
    assert validator.is_valid("test.mobi", mobi_book_from_fs)


@pytest.mark.parametrize(
    "book,expected",
    [
        ("fb2_book_from_fs", Mimetype.FB2),
        ("zipped_fb2_book_from_fs", Mimetype.FB2_ZIP),
        ("epub_book_from_fs", Mimetype.EPUB),
        ("mobi_book_from_fs", Mimetype.MOBI),
        ("wrong_encoded_fb2_zip", Mimetype.FB2_ZIP),
    ],
)
def test_detect_mime_service(book, expected, request) -> None:
    actual = detect_mime_service(request.getfixturevalue(book), "test_book")
    assert actual == expected
