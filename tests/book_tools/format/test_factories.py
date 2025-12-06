import pytest
from pytest_factoryboy import register
from tests.book_tools.format.helpers import (
    Author,
    AuthorFactory,
    Image,
    ImageFactory,
    # Series,
    SeriesFactory,
    EBookData,
    EBookDataFactory,
)

register(AuthorFactory)
register(ImageFactory)
register(SeriesFactory)
register(EBookDataFactory)


def test_author_factory(author):
    author = author
    assert isinstance(author, Author)


@pytest.mark.parametrize("author__first_name", ["test"])
def test_parametrized_author_factory(author, author__first_name):
    author = author
    assert isinstance(author, Author)
    assert "test" == author.first_name


def test_image_factory(image):
    img = image
    assert isinstance(img, Image)
    assert img.type == "image/jpeg"
    assert isinstance(img.content, bytes)


def test_fiction_book(e_book_data):
    assert isinstance(e_book_data, EBookData)
