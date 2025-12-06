import pytest

from io import BytesIO
from contextlib import nullcontext
from book_tools.services import extract_fb2_metadata_service
from tests.book_tools.format.helpers import fb2_book_fabric

from book_tools.format.fb2 import (
    FB2,
    # FB2Zip,
)

from book_tools.exceptions import FB2StructureException


# @pytest.mark.skip
# def test_fb2_book_fabric(
#     namespace,
#     title,
#     authors,
#     genres,
#     lang,
#     docdate,
#     series_name,
#     series_no,
#     annotation,
#     correct,
# ) -> None:
#     book_xml = fb2_book_fabric(
#         namespace,
#         title,
#         authors,
#         genres,
#         lang,
#         docdate,
#         series_name,
#         series_no,
#         annotation,
#         correct=True,
#     )
#     assert book_xml is not None


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
    result = extract_fb2_metadata_service(virtual_fb2_book, "Test Book")
    assert result is not None


def test_fb2_metadata_service_returns_the_same(virtual_fb2_book) -> None:
    actual = extract_fb2_metadata_service(virtual_fb2_book, "Test Book")
    expected = FB2(virtual_fb2_book, "Test Book")
    assert actual == expected
