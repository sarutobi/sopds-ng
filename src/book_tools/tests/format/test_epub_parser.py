import pytest
import os

from book_tools.format.epub import EPub, EPub_new
from opds_catalog.tests.helpers import read_file_as_iobytes
from book_tools.tests.format.helpers import book_file_are_equals


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
    assert book_file_are_equals(book_actual, book_new)
