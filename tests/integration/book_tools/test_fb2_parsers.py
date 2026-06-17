import pytest

from book_tools.format.fb2 import (
    FB2,
)
from book_tools.format.fb2sax import FB2sax
from book_tools.format.parsers import (
    FB2 as FB2_new,
)
from book_tools.format.parsers import FB2sax as FB2sax_new


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


def test_fb2sax(get_file_content, simple_fb2) -> None:
    # file = read_file_as_iobytes(os.path.join(test_rootlib, "262001.fb2"))
    book_file = FB2sax(get_file_content(simple_fb2), "Test Book")
    assert book_file is not None
    assert book_file.docdate == "30.1.2011"
    assert book_file.title == "The Sanctuary Sparrow"


@pytest.mark.benchmark
def test_benchmark_fb2sax_new_parser(benchmark, virtual_fb2_book):
    benchmark(FB2sax_new, virtual_fb2_book, "benchmark")


@pytest.mark.benchmark
def test_benchmark_fb2sax_parser(benchmark, virtual_fb2_book):
    benchmark(FB2sax, virtual_fb2_book, "benchmark")


@pytest.mark.benchmark
def test_benchmark_fb2_new_parser(benchmark, virtual_fb2_book):
    benchmark(FB2_new, virtual_fb2_book)


@pytest.mark.benchmark
def test_benchmark_fb2_parser(benchmark, virtual_fb2_book):
    benchmark(FB2, virtual_fb2_book, "benchmark")


def test_fb2_cover_extraction(fb2_with_cover) -> None:
    """Проверка извлечения обложки старым и новым парсером FB2."""
    cover_actual = FB2(fb2_with_cover, "Test book").extract_cover_memory()
    cover_expected = FB2_new(fb2_with_cover).extract_cover()
    assert cover_actual is not None
    assert cover_actual == cover_expected


def test_fb2sax_cover_extraction(fb2_book_from_fs) -> None:
    """Проверка извлечения обложки старым и новым парсером FB2sax"""
    cover_actual = FB2sax(fb2_book_from_fs, "Test book").extract_cover_memory()
    cover_expected = FB2sax_new(fb2_book_from_fs, "Test book").extract_cover()
    assert cover_expected is not None
    assert cover_actual == cover_expected
