import pytest

from contextlib import nullcontext

import os

from zipfile import BadZipFile

from book_tools.format.fb2sax import FB2sax, FB2sax_new, FB2StructureException
from book_tools.format.fb2 import (
    FB2,
    FB2_new,
    FB2Zip,
    FB2Zip_new,
    FB2StructureException as FB2_StructureException,
)
from book_tools.format.mimetype import Mimetype

from opds_catalog.tests.helpers import read_file_as_iobytes


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
    file = read_file_as_iobytes(os.path.join(test_rootlib, "262001.fb2"))
    book_file = FB2sax(file, "Test Book")
    assert book_file is not None
    assert book_file.docdate == "30.1.2011"
    assert book_file.title == "The Sanctuary Sparrow"


@pytest.mark.parametrize(
    "book, expected_exception",
    [
        ("262001.fb2", nullcontext()),
        ("badfile.fb2", pytest.raises(FB2StructureException)),
        ("badfile2.fb2", pytest.raises(FB2StructureException)),
    ],
)
def test_fb2sax_new(test_rootlib, book, expected_exception) -> None:
    file = read_file_as_iobytes(os.path.join(test_rootlib, book))
    with expected_exception:
        book_actual = FB2sax(file, "Test Book")
        book_new = FB2sax_new(file, "Test Book").parse_book_data(file, "Test Book")
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


@pytest.mark.parametrize(
    "book, expected_exception",
    [
        ("262001.fb2", nullcontext()),
        ("badfile.fb2", pytest.raises(FB2_StructureException)),
        ("badfile2.fb2", pytest.raises(FB2_StructureException)),
    ],
)
def test_fb2_new(test_rootlib, book, expected_exception) -> None:
    file = read_file_as_iobytes(os.path.join(test_rootlib, book))
    with expected_exception:
        book_actual = FB2(file, "Test Book")
        book_new = FB2_new(file, "Test Book").parse_book_data(
            file, "Test Book", Mimetype.FB2
        )
        assert book_actual == book_new


@pytest.mark.parametrize(
    "book, expected_exception",
    [
        ("262001.zip", nullcontext()),
        ("badfile.zip", pytest.raises(BadZipFile)),
        ("badfile2.zip", pytest.raises(FB2_StructureException)),
        ("books.zip", pytest.raises(FB2_StructureException)),
    ],
)
def test_fb2zip_new(test_rootlib, book, expected_exception) -> None:
    file = read_file_as_iobytes(os.path.join(test_rootlib, book))
    with expected_exception:
        book_actual = FB2Zip(file, "Test Book")
        book_new = FB2Zip_new(file, "Test Book").parse_book_data(
            file, "Test Book", Mimetype.FB2_ZIP
        )
        assert book_actual == book_new
