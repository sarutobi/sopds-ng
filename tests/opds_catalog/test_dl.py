# -*- coding: utf-8 -*-

import base64
import os
import zipfile
from pathlib import Path

import pytest
from constance import config
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from opds_catalog import opdsdb
from opds_catalog.dl import (
    get_fs_book_path,
    getFileData,
    getFileDataConv,
    getFileDataZip,
    getFileName,
    read_from_regular_file,
    read_from_zipped_file,
)
from opds_catalog.models import Book
from tests.opds_catalog.helpers import (
    BookFactoryMixin,
    create_book,
    read_book_from_zip_file,
    read_file_as_iobytes,
)


@pytest.fixture
def django_user(django_user_model):
    user = django_user_model.objects.create_user(username="test", password="secret")
    yield user


@pytest.fixture
def auth_client(client, django_user):
    client.force_login(django_user)
    yield client


@pytest.fixture
def load_db_data(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("loaddata", "testdb.json")


@pytest.fixture
def create_regular_book():
    book = create_book(filename="262001.fb2", cat_type=opdsdb.CAT_NORMAL, path=".")
    book.save()
    yield book


@pytest.mark.usefixtures("fake_sopds_root_lib", "django_user", "load_db_data")
@pytest.mark.django_db
class TestDownloads(object):
    fixtures = ["testdb.json"]

    @pytest.mark.override_config(SOPDS_AUTH=True)
    def test_unauthorized_downloads(self, client):
        response = client.get(reverse("opds:download", args=(5, 0)))
        assert response.status_code == 401

    @pytest.mark.override_config(SOPDS_AUTH=True)
    def test_authorized_download_book(self, client, django_user):
        client.force_login(django_user)
        response = client.get(reverse("opds:download", args=(5, 0)))
        assert response.status_code == 200
        assert response["Content-Length"] == "495373"

    @pytest.mark.override_config(SOPDS_AUTH=True)
    def test_basic_authentication(self, client, django_user, django_user_model) -> None:
        response = client.get(reverse("opds:download", args=(5, 0)))
        assert response.status_code == 401
        credentials = "test:secret"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        authorization_header = f"Basic {encoded_credentials}"
        response = client.get(
            reverse("opds:download", args=(5, 0)),
            HTTP_AUTHORIZATION=authorization_header,
        )
        assert response.status_code == 200
        assert response["Content-Length"] == "495373"

    @pytest.mark.override_config(SOPDS_AUTH=False)
    def test_download_zip(self, client):
        response = client.get(reverse("opds:download", args=(5, 1)))
        assert response.status_code == 200
        assert response["Content-Length"] == "219508"


class TestGetFileName(TestCase, BookFactoryMixin):
    def setUp(self) -> None:
        self.book = self.setup_book(title="Книга", format="fb2", filename="123abc.zip")

    @pytest.mark.override_config(SOPDS_TITLE_AS_FILENAME=False)
    def test_by_filename(self) -> None:
        expected_filename = self.book.filename

        test_filename = getFileName(self.book)
        assert test_filename == expected_filename

    @pytest.mark.override_config(SOPDS_TITLE_AS_FILENAME=True)
    def test_by_title(self) -> None:
        expected_filename = "Kniga.fb2"
        test_filename = getFileName(self.book)
        assert test_filename == expected_filename

    @pytest.mark.override_config(SOPDS_TITLE_AS_FILENAME=False)
    def test_by_russian_filename(self) -> None:
        book = self.setup_book(title="Книга", format="fb2", filename="Книга.zip")
        expected_filename = "Kniga.zip"
        test_filename = getFileName(book)
        assert test_filename == expected_filename


@pytest.mark.usefixtures("fake_sopds_root_lib")
class TestReadFromRegularFile(TestCase, BookFactoryMixin):
    """Тесты для чтения содержимого обычных файлов"""

    def test_read_book_from_regular_file(self) -> None:
        book = self.setup_regular_book(filename="262001.fb2", path=".")
        expected = read_file_as_iobytes(
            os.path.join(config.SOPDS_ROOT_LIB, book.filename)
        )
        assert expected is not None

        actual = read_from_regular_file(
            os.path.join(get_fs_book_path(book), book.filename)
        )
        assert actual.getvalue() == expected.getvalue()

    def test_read_from_unexistent_file(self) -> None:
        book = self.setup_regular_book(filename="263001.fb2", path=".")
        actual = read_from_regular_file(
            os.path.join(get_fs_book_path(book), book.filename)
        )
        assert actual is None


@pytest.mark.usefixtures("fake_sopds_root_lib")
class TestReadFromZippedFile(TestCase, BookFactoryMixin):
    """Тесты чтения из архивных файлов"""

    # def setUp(self) -> None:
    #     self.root_library = config.SOPDS_ROOT_LIB
    #
    # def tearDown(self) -> None:
    #     config.SOPDS_ROOT_LIB = self.root_library

    def test_read_book_from_zip_file(self):
        book = self.setup_zipped_book(filename="539273.fb2", path="books.zip")
        expected = read_book_from_zip_file(
            os.path.join(config.SOPDS_ROOT_LIB, book.path), book.filename
        )
        assert expected is not None

        actual = read_from_zipped_file(
            os.path.join(config.SOPDS_ROOT_LIB, book.path), book.filename
        )
        assert actual.getvalue() == expected.getvalue()

    def test_no_book_in_zip_file(self):
        book = self.setup_zipped_book(filename="559273.fb2", path="books.zip")

        actual = read_from_zipped_file(
            os.path.join(config.SOPDS_ROOT_LIB, book.path), book.filename
        )
        assert actual is None

    def test_read_book_from_non_existent_zip_file(self):
        book = self.setup_zipped_book(filename="559273.fb2", path="books1.zip")

        actual = read_from_zipped_file(
            os.path.join(config.SOPDS_ROOT_LIB, book.path), book.filename
        )
        assert actual is None


@pytest.mark.usefixtures("fake_sopds_root_lib")
class TestGetFileData(TestCase, BookFactoryMixin):
    # def setUp(self) -> None:
    #     self.root_library = config.SOPDS_ROOT_LIB
    #
    # def tearDown(self) -> None:
    #     config.SOPDS_ROOT_LIB = self.root_library

    def test_read_book_from_regular_file(self) -> None:
        book = self.setup_regular_book(filename="262001.fb2", path=".")
        expected = read_file_as_iobytes(
            os.path.join(config.SOPDS_ROOT_LIB, book.filename)
        )
        assert expected is not None

        actual = getFileData(book)
        assert actual.getvalue() == expected.getvalue()

    def test_read_book_from_zip_file(self) -> None:
        book = self.setup_zipped_book(filename="539273.fb2", path="books.zip")
        expected = read_book_from_zip_file(
            os.path.join(config.SOPDS_ROOT_LIB, book.path), book.filename
        )
        assert expected is not None

        actual = getFileData(book)
        assert actual.getvalue() == expected.getvalue()

    def test_read_book_from_inp_file(self) -> None:
        expected = read_book_from_zip_file(
            os.path.join(os.path.dirname(Path(__file__)), "data/books.zip"),
            "539273.fb2",
        )
        assert expected is not None

        book = Book(filename="539273.fb2", cat_type=3, path="inpx/inp/books.zip")
        actual = getFileData(book)
        assert actual.getvalue() == expected.getvalue()

    def test_read_absent_book(self) -> None:
        # Проверки чтения данных из несуществующих файлов
        book = Book(filename="263001.fb2", cat_type=0, path="data")
        actual = getFileData(book)
        assert actual is None

        book = Book(filename="539273.fb2", cat_type=1, path="data/books1.zip")
        actual = getFileData(book)
        assert actual is None

        book = Book(filename="559273.fb2", cat_type=1, path="data/books.zip")
        actual = getFileData(book)
        assert actual is None

        book = Book(filename="539273.fb2", cat_type=3, path="data/inpx/inp/books1.zip")
        actual = getFileData(book)
        assert actual is None

        book = Book(filename="559273.fb2", cat_type=3, path="data/inpx/inp/books.zip")
        actual = getFileData(book)
        assert actual is None


@pytest.mark.usefixtures("fake_sopds_root_lib")
class TestGetFileDataZip(TestCase):
    # def setUp(self) -> None:
    #     self.root_library = config.SOPDS_ROOT_LIB
    #
    # def tearDown(self) -> None:
    #     config.SOPDS_ROOT_LIB = self.root_library

    def test_create_zip_stream(self) -> None:
        expected_file_name = "zip_book.fb2"
        expected_content = read_file_as_iobytes(
            os.path.join(os.path.dirname(Path(__file__)), "data/262001.fb2")
        )
        book = Book(
            title="zip book",
            format="fb2",
            filename="262001.fb2",
            cat_type=0,
            path=".",
        )

        actual = getFileDataZip(book)
        with zipfile.ZipFile(actual, "r") as tested:
            assert expected_file_name in tested.namelist()
            actual_content = tested.read(expected_file_name)
            assert expected_content.getvalue() == actual_content


@pytest.mark.override_config(SOPDS_ROOT_LIB="opds_catalog/tests/data/")
@pytest.mark.django_db
class TestGetFsBookPath(object):
    def test_inp_book_path(self) -> None:
        book = Book(filename="539273.fb2", cat_type=3, path="inpx/inp/books.zip")
        expected_path = "opds_catalog/tests/data/books.zip"
        actual_path = get_fs_book_path(book)
        assert actual_path == expected_path

    def test_normal_book_path(self) -> None:
        book = Book(filename="539273.fb2", cat_type=0, path="books.zip")
        expected_path = "opds_catalog/tests/data/books.zip"
        actual_path = get_fs_book_path(book)
        assert actual_path is not None
        assert actual_path == expected_path


@pytest.mark.usefixtures("fake_sopds_root_lib")
@pytest.mark.django_db
class TestGetFileDataConv(object):
    def test_convert_non_fb2_book(self) -> None:
        book = Book(title="Not a fb2 book", format="pdf")
        actual = getFileDataConv(book, "epub")
        assert actual is None

    def test_convert_absent_book(self) -> None:
        book = Book(
            title="I'm not exists", filename="263001.fb2", cat_type="0", path="data"
        )
        actual = getFileDataConv(book, "epub")
        assert actual is None


@pytest.mark.django_db
def test_get_book_cover(fake_sopds_root_lib, create_regular_book, client) -> None:
    book = create_regular_book
    assert getFileData(book)
    url = reverse("opds:cover", args=(book.id,))
    actual = client.get(url)
    assert actual.status_code == 200
    assert actual["Content-Length"] == "56360"
