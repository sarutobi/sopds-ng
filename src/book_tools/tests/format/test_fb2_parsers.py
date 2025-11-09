# import os
# from contextlib import nullcontext
from io import BytesIO
# from zipfile import BadZipFile

# import pytest

from book_tools.format.bookfile import BookFile
from book_tools.format.fb2 import (
    FB2,
    # FB2Zip,
)

# from book_tools.format.fb2 import (
#     FB2StructureException as FB2_StructureException,
# )
from book_tools.format.fb2sax import FB2sax
from book_tools.format.parsers import FB2sax as FB2sax_new
from book_tools.format.mimetype import Mimetype
from book_tools.format.parsers import (
    EbookMetaParser,
)
from book_tools.format.parsers import (
    FB2Base as FB2_new,
)
# from book_tools.exceptions import FB2StructureException

# from book_tools.format.parsers import (
# FB2Zip as FB2Zip_new,
# )
from book_tools.tests.format.helpers import fb2_book_fabric
# from opds_catalog.tests.helpers import read_file_as_iobytes


def test_fb2tag_tagopen(test_tag) -> None:
    test_attrs = [
        "test1",
    ]
    for tag in ("FictionBook", "description", "title-info", "author"):
        assert not test_tag.tagopen(tag, test_attrs)
        assert test_attrs != test_tag.attrs

    assert test_tag.tagopen("first-name", test_attrs)
    assert test_attrs == test_tag.attrs


def test_fb2tag_icorrect_path_tagopen(test_tag) -> None:
    test_attrs = [
        "test1",
    ]
    for tag in ("FictionBook", "description", "document-info", "author"):
        assert not test_tag.tagopen(tag, test_attrs)
        assert test_attrs != test_tag.attrs

    assert not test_tag.tagopen("first-name", test_attrs)
    assert test_attrs != test_tag.attrs


def test_fb2tag_setvalue(test_tag) -> None:
    for tag in ("FictionBook", "description", "title-info", "author"):
        test_tag.tagopen(tag)
        test_tag.setvalue("test")
        assert not test_tag.process_value
        assert test_tag.current_value != "test"

    assert test_tag.tagopen("first-name")
    assert not test_tag.process_value

    test_tag.setvalue("test")
    assert test_tag.process_value
    assert test_tag.current_value == "test"


def test_fb2sax(test_rootlib) -> None:
    book = fb2_book_fabric(title="The Sanctuary Sparrow", docdate="30.1.2011")

    # file = read_file_as_iobytes(os.path.join(test_rootlib, "262001.fb2"))
    book_file = FB2sax(BytesIO(book), "Test Book")
    assert book_file is not None
    assert book_file.docdate == "30.1.2011"
    assert book_file.title == "The Sanctuary Sparrow"


def test_fb2sax_new_parser(virtual_fb2_book) -> None:
    book_actual = FB2sax(virtual_fb2_book, "Test Book")
    book_new = FB2sax_new(virtual_fb2_book, "Test Book")
    assert _are_equals_data(book_actual, book_new)


def test_fb2_new_parser(virtual_fb2_book) -> None:
    book_actual = FB2(virtual_fb2_book, "Test Book")
    book_new = FB2_new(virtual_fb2_book, "Test Book", Mimetype.FB2)
    assert _are_equals_data(book_actual, book_new)


def _are_equals_data(bookfile: BookFile, parser: EbookMetaParser) -> bool:
    # Парсер возвращает перечень авторов в виде списка кортежей, а в описателе
    # книги список авторов хранится в словаре, поэтому делаем преобразование
    expected_authors: list[dict[str, str]] = []
    for a in parser.authors:
        name, skey = a
        author = {"name": name, "sortkey": skey.lower()}
        expected_authors.append(author)

    return (
        bookfile.title == parser.title
        and bookfile.description == parser.description
        and (sorted(bookfile.authors) == sorted(expected_authors))
        and (sorted(bookfile.tags) == sorted(parser.tags))
        and bookfile.series_info == parser.series_info
        and bookfile.language_code == parser.language_code
        and bookfile.docdate == parser.docdate
    )


def test_benchmark_fb2sax_new_parser(benchmark, virtual_fb2_book):
    benchmark(FB2sax_new, virtual_fb2_book, "benchmark")


def test_benchmark_fb2sax_parser(benchmark, virtual_fb2_book):
    benchmark(FB2sax, virtual_fb2_book, "benchmark")


def test_benchmark_fb2_new_parser(benchmark, virtual_fb2_book):
    benchmark(FB2_new, virtual_fb2_book, "benchmark", "test")


def test_benchmark_fb2_parser(benchmark, virtual_fb2_book):
    benchmark(FB2, virtual_fb2_book, "benchmark")


# @pytest.mark.parametrize(
#     "book, expected_exception",
#     [
#         ("262001.zip", nullcontext()),
#         ("badfile.zip", pytest.raises(BadZipFile)),
#         ("badfile2.zip", pytest.raises(FB2_StructureException)),
#         ("books.zip", pytest.raises(FB2_StructureException)),
#     ],
# )
# def test_fb2zip_new(test_rootlib, book, expected_exception) -> None:
#     file = read_file_as_iobytes(os.path.join(test_rootlib, book))
#     with expected_exception:
#         book_actual = FB2Zip(file, "Test Book")
#         book_new = FB2Zip_new(file, "Test Book").parse_book_data(
#             file, "Test Book", Mimetype.FB2_ZIP
#         )
#         assert book_actual == book_new
