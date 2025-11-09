from .helpers import FictionBook, fb2_book_fabric
from book_tools.format.fb2 import FB2

# import pytest
import io


# @pytest.fixture
# def fb_generator() -> FictionBook:
#     return FictionBook()


def test_fictionbook_class() -> None:
    fb_generator = FictionBook()
    assert fb_generator is not None


def test_generate_book(fb_generator) -> None:
    result = fb_generator.build()
    assert result is not None
    assert b"FictionBook" in result
    assert b"<description>" in result
    assert b"<title-info>" in result


def test_book_title(fb_generator) -> None:
    fb_generator.title = "Test Book"
    result = fb_generator.build()
    assert b"<book-title>" in result
    assert b"Test Book" in result


def test_book_author(fb_generator) -> None:
    fb_generator.add_author("First", "Middle", "Second")
    result = fb_generator.build()
    assert b"<author>" in result
    assert b"First" in result
    assert b"Middle" in result
    assert b"Second" in result


def test_book_fabric() -> None:
    book = fb2_book_fabric()
    result = FB2(io.BytesIO(book), "test")
    assert result is not None

    assert result.title == "Generated Book"
    assert len(result.tags) == 2
    assert result.language_code == "en"
