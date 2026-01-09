"""Фикстуры для модуля book_tools"""

from io import BytesIO

import pytest

from book_tools.format.fb2 import Namespace
from book_tools.format.fb2sax import fb2tag
from book_tools.format.parsers import EbookMetaParser, EpubParser
from opds_catalog import opdsdb
from tests.book_tools.format.helpers import Author, fb2_book_fabric
from tests.opds_catalog.helpers import create_book


@pytest.fixture(scope="module")
def epub_parser(epub_book_from_fs) -> EbookMetaParser:
    """Парсер формата EPub"""
    return EpubParser(epub_book_from_fs)


@pytest.fixture(scope="module")
def invalid_epub(zipped_fb2_book_from_fs) -> BytesIO:
    """Некорректный тип книги в формате EPub"""
    return zipped_fb2_book_from_fs


@pytest.fixture
def test_tag() -> fb2tag:
    # TODO: перенести фикстуру в пакет тестов fb2sax
    return fb2tag(("description", "title-info", "author", "first-name"))


@pytest.fixture(params=(None, Namespace.FICTION_BOOK20, Namespace.FICTION_BOOK21))
def namespace(request):
    """Предоставляет различные неймспейсы для книг в формате fb2"""
    return request.param


@pytest.fixture(params=(None, "", "Generated Book"))
def title(request):
    return request.param


@pytest.fixture(
    params=(
        None,
        [],
        [
            Author("Pytest", last_name="Genius"),
        ],
        [
            Author("Pytest", last_name="Genius"),
            Author("Pytest", "Another", "Genius"),
        ],
    )
)
def authors(request):
    return request.param


@pytest.fixture(
    params=(
        None,
        [],
        [
            "genre1",
        ],
        [
            "genre1",
            "genre2",
        ],
    )
)
def genres(request):
    print(request)
    return request.param


@pytest.fixture(params=(None, "", "ru"))
def lang(request):
    return request.param


@pytest.fixture(params=(None, "", "1970-01-01"))
def docdate(request):
    return request.param


@pytest.fixture(params=(None, "", "Test annotation"))
def annotation(request):
    return request.param


@pytest.fixture(params=(None, "", "Test series"))
def series_name(request):
    return request.param


@pytest.fixture(params=(None, "", 1))
def series_no(request):
    return request.param


@pytest.fixture(params=(True, False))
def correct(request):
    return request.param


# @pytest.fixture
# def fb2_book_fabric(
#     namespace,
#     # namespace: str | None = Namespace.FICTION_BOOK20,
#     title,
#     authors,
#     genres,
#     lang="en",
#     docdate="01.01.1970",
#     series_name=None,
#     series_no=None,
#     annotation="<p>Somedescription</p>",
#     correct=True,
# ) -> bytes:
#     book = FictionBook()
#     book.title = title
#     book.authors = authors
#     book.genres = genres
#     book.lang = lang
#     book.docdate = docdate
#     data = book.build(namespace)
#     if not correct:
#         data = data.replace(b"genre>", b"genre", 1)
#     return data


# @pytest.fixture
# def fb_generator() -> EBookData:
#     return EBookData()


@pytest.fixture
def create_regular_book():
    # TODO: переименовать фикстуру
    book = create_book(filename="262001.fb2", cat_type=opdsdb.CAT_NORMAL, path=".")
    book.save()
    return book


@pytest.fixture
def virtual_fb2_book(namespace) -> BytesIO:
    """Формирует виртуальную книгу в формате FB2"""
    return BytesIO(fb2_book_fabric(namespace=namespace))


# @pytest.fixture
# def author_factory():
#     return AuthorFactory()


@pytest.fixture
def create_incorrect_book():
    return BytesIO(b"I'm not a fiction book")
