from .helpers import EBookData, fb2_book_fabric
from book_tools.format.fb2 import FB2
from .helpers import Author

import pytest
import io


@pytest.fixture(params=[{"title": None, "authors": None}])
def fb_generator(request) -> bytes:
    return fb2_book_fabric(
        title=request.param["title"], authors=request.param["authors"]
    )


# def test_fictionbook_class() -> None:
#     fb_generator = EBookData()
#     assert fb_generator is not None


def test_generate_book(fb_generator) -> None:
    result = fb_generator
    assert result is not None
    assert b"FictionBook" in result
    assert b"<description>" in result
    assert b"<title-info>" in result


@pytest.mark.parametrize(
    "fb_generator",
    [
        {"title": "Test Book", "authors": None},
    ],
    indirect=True,
)
def test_book_title(fb_generator) -> None:
    result = fb_generator
    assert b"<book-title>" in result
    assert b"Test Book" in result


@pytest.mark.parametrize(
    "fb_generator",
    [
        {"title": None, "authors": [Author("First", "Middle", "Second")]},
    ],
    indirect=True,
)
def test_book_author(fb_generator) -> None:
    result = fb_generator
    assert b"<author>" in result
    assert b"First" in result
    assert b"Middle" in result
    assert b"Second" in result


def test_book_fabric() -> None:
    book = fb2_book_fabric(title="Generated Book")
    result = FB2(io.BytesIO(book), "test")
    assert result is not None

    assert result.title == "Generated Book"
    assert len(result.tags) == 2
    assert result.language_code == "ru"
