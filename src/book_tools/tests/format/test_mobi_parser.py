import pytest
import os

from book_tools.format.mobi import Mobipocket, Mobipocket_new
from book_tools.tests.format.helpers import book_file_are_equals

from opds_catalog.tests.helpers import read_file_as_iobytes


@pytest.mark.parametrize(
    "book",
    [
        "robin_cook.mobi",
    ],
)
def test_mobi_parser(test_rootlib, book) -> None:
    file = read_file_as_iobytes(os.path.join(test_rootlib, book))
    book_actual = Mobipocket(file, "Test Book")
    book_new = Mobipocket_new(file, "Test Book").parse_book_data(file, "Test Book")
    assert book_file_are_equals(book_actual, book_new)
