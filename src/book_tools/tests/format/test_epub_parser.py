import pytest
import os

from book_tools.format.epub import EPub, EPub_new
from opds_catalog.tests.helpers import read_file_as_iobytes

from .test_fb2_parsers import test_rootlib


@pytest.mark.parametrize(
    "book",
    [
        "mirer.epub",
    ],
)
def test_epub_parser(test_rootlib, book) -> None:
    file = read_file_as_iobytes(os.path.join(test_rootlib, book))
    book_actual = EPub(file, "Test Book")
    book_new = EPub_new(file, "Test Book").parse_book_data(file, "Test Book")
    assert book_actual is not None
    assert book_new is not None

    assert book_actual.file == book_new.file
    assert book_actual.mimetype == book_new.mimetype
    assert book_actual.original_filename == book_new.original_filename
    assert book_actual.title == book_new.title
    assert book_actual.description == book_new.description
    assert book_actual.authors == book_new.authors
    assert book_actual.tags == book_new.tags
    assert book_actual.series_info == book_new.series_info
    assert book_actual.language_code == book_new.language_code
    assert book_actual.issues == book_new.issues
    assert book_actual.docdate == book_new.docdate
