"""Общие фикстуры для модуля book_tools"""

import pytest
import os
import io
from pathlib import Path
from book_tools.format.fb2sax import fb2tag
from tests.book_tools.format.helpers import EBookData, Author
from book_tools.format.fb2 import Namespace
from tests.opds_catalog.helpers import create_book
from opds_catalog import opdsdb
from tests.book_tools.format.helpers import fb2_book_fabric


@pytest.fixture
def test_tag() -> fb2tag:
    # TODO: перенести фиктсуру в пакет тестов fb2sax
    return fb2tag(("description", "title-info", "author", "first-name"))


@pytest.fixture
def test_rootlib() -> str:
    # TODO: Перенести фиктуру в общие для проекта фикстуры
    test_module_path: str = os.path.dirname(os.path.dirname(Path(__file__).resolve()))
    test_ROOTLIB = os.path.join(test_module_path, "opds_catalog/data")
    return test_ROOTLIB


@pytest.fixture(params=(None, Namespace.FICTION_BOOK20, Namespace.FICTION_BOOK21))
def namespace(request):
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


# @pytest.fixture
# def manage_sopds_root_lib():
#     # TODO: перенести фикстуру в общие фиктуры проекта
#     backup = config.SOPDS_ROOT_LIB
#     config.SOPDS_ROOT_LIB = os.path.join(settings.BASE_DIR, "opds_catalog/tests/data/")
#     yield config
#     config.SOPDS_ROOT_LIB = backup


@pytest.fixture
def create_regular_book():
    # TODO: переименовать фикстуру
    book = create_book(filename="262001.fb2", cat_type=opdsdb.CAT_NORMAL, path=".")
    book.save()
    return book


@pytest.fixture
def virtual_fb2_book(namespace) -> io.BytesIO:
    return io.BytesIO(fb2_book_fabric(namespace=namespace))


# @pytest.fixture
# def author_factory():
#     return AuthorFactory()


@pytest.fixture
def create_incorrect_book():
    return io.BytesIO(b"I'm not a fiction book")
