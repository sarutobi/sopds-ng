# -*- coding: utf-8 -*-

import zipfile
import os
import pytest
import base64
from opds_catalog import opdsdb

from constance import config
from django.contrib.auth.models import User
from django.conf import settings
from django.urls import reverse
from django.test import TestCase, Client

from opds_catalog.dl import (
    getFileName,
    getFileData,
    getFileDataZip,
    get_fs_book_path,
    getFileDataConv,
    read_from_regular_file,
    read_from_zipped_file,
)
from opds_catalog.models import Book

from .helpers import (
    read_file_as_iobytes,
    read_book_from_zip_file,
    BookFactoryMixin,
    create_book,
)


class DownloadsTestCase(TestCase):
    fixtures = ["testdb.json"]

    def setUp(self) -> None:
        self.root_library = config.SOPDS_ROOT_LIB
        config.SOPDS_ROOT_LIB = os.path.join(
            settings.BASE_DIR, "opds_catalog/tests/data/"
        )
        config.SOPDS_AUTH = False
        User.objects.create_user("test", "test@sopds.ng", "secret")
        self.c = Client()

    def tearDown(self) -> None:
        config.SOPDS_ROOT_LIB = self.root_library

    def test_unauthorized_downloads(self):
        config.SOPDS_AUTH = True
        response = self.c.get(reverse("opds:download", args=(5, 0)))
        self.assertEqual(response.status_code, 401)

    def test_authorized_download_book(self):
        config.SOPDS_AUTH = True
        self.c.login(username="test", password="secret")
        response = self.c.get(reverse("opds:download", args=(5, 0)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Length"], "495373")

    def test_basic_authentication(self) -> None:
        config.SOPDS_AUTH = True
        response = self.c.get(reverse("opds:download", args=(5, 0)))
        self.assertEqual(response.status_code, 401)
        credentials = "test:secret"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        authorization_header = f"Basic {encoded_credentials}"
        response = self.c.get(
            reverse("opds:download", args=(5, 0)),
            HTTP_AUTHORIZATION=authorization_header,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Length"], "495373")

    def test_download_zip(self):
        response = self.c.get(reverse("opds:download", args=(5, 1)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Length"], "219508")
        print(response)


class TestGetFileName(TestCase, BookFactoryMixin):
    def setUp(self) -> None:
        self.book = self.setup_book(title="Книга", format="fb2", filename="123abc.zip")
        self.title_as_filename = config.SOPDS_TITLE_AS_FILENAME

    def tearDown(self) -> None:
        config.SOPDS_TITLE_AS_FILENAME = self.title_as_filename

    def test_by_filename(self) -> None:
        expected_filename = self.book.filename
        config.SOPDS_TITLE_AS_FILENAME = False

        test_filename = getFileName(self.book)
        self.assertEqual(test_filename, expected_filename)

    def test_by_title(self) -> None:
        config.SOPDS_TITLE_AS_FILENAME = True
        expected_filename = "Kniga.fb2"
        test_filename = getFileName(self.book)
        self.assertEqual(test_filename, expected_filename)

    def test_by_russian_filename(self) -> None:
        book = self.setup_book(title="Книга", format="fb2", filename="Книга.zip")
        config.SOPDS_TITLE_AS_FILENAME = False
        expected_filename = "Kniga.zip"
        test_filename = getFileName(book)
        self.assertEqual(test_filename, expected_filename)


class TestReadFromRegularFile(TestCase, BookFactoryMixin):
    """Тесты для чтения содержимого обычных файлов"""

    def setUp(self) -> None:
        self.root_library = config.SOPDS_ROOT_LIB
        config.SOPDS_ROOT_LIB = "opds_catalog/tests/"

    def tearDown(self) -> None:
        config.SOPDS_ROOT_LIB = self.root_library

    def test_read_book_from_regular_file(self) -> None:
        book = self.setup_regular_book(filename="262001.fb2", path="data")
        expected = read_file_as_iobytes(
            os.path.join(config.SOPDS_ROOT_LIB, book.path, book.filename)
        )
        self.assertIsNotNone(expected)

        actual = read_from_regular_file(
            os.path.join(get_fs_book_path(book), book.filename)
        )
        self.assertEqual(actual.getvalue(), expected.getvalue())

    def test_read_from_unexistent_file(self) -> None:
        # book = Book(filename="263001.fb2", cat_type=0, path="data")
        book = self.setup_regular_book(filename="263001.fb2", path="data")
        actual = read_from_regular_file(
            os.path.join(get_fs_book_path(book), book.filename)
        )
        self.assertIsNone(actual)


class TestReadFromZippedFile(TestCase, BookFactoryMixin):
    """Тесты чтения из архивных файлов"""

    def setUp(self) -> None:
        self.root_library = config.SOPDS_ROOT_LIB
        config.SOPDS_ROOT_LIB = "opds_catalog/tests/"

    def tearDown(self) -> None:
        config.SOPDS_ROOT_LIB = self.root_library

    def test_read_book_from_zip_file(self):
        book = self.setup_zipped_book(filename="539273.fb2", path="data/books.zip")
        expected = read_book_from_zip_file(
            os.path.join(config.SOPDS_ROOT_LIB, book.path), book.filename
        )
        self.assertIsNotNone(expected)

        actual = read_from_zipped_file(
            os.path.join(config.SOPDS_ROOT_LIB, book.path), book.filename
        )
        self.assertEqual(actual.getvalue(), expected.getvalue())

    def test_no_book_in_zip_file(self):
        book = self.setup_zipped_book(filename="559273.fb2", path="data/books.zip")

        actual = read_from_zipped_file(
            os.path.join(config.SOPDS_ROOT_LIB, book.path), book.filename
        )
        self.assertIsNone(actual)

    def test_read_book_from_non_existent_zip_file(self):
        book = self.setup_zipped_book(filename="559273.fb2", path="data/books1.zip")

        actual = read_from_zipped_file(
            os.path.join(config.SOPDS_ROOT_LIB, book.path), book.filename
        )
        self.assertIsNone(actual)


class TestGetFileData(TestCase, BookFactoryMixin):
    def setUp(self) -> None:
        self.root_library = config.SOPDS_ROOT_LIB
        config.SOPDS_ROOT_LIB = "opds_catalog/tests/"

    def tearDown(self) -> None:
        config.SOPDS_ROOT_LIB = self.root_library

    def test_read_book_from_regular_file(self) -> None:
        book = self.setup_regular_book(filename="262001.fb2", path="data")
        expected = read_file_as_iobytes(
            os.path.join(config.SOPDS_ROOT_LIB, book.path, book.filename)
        )
        self.assertIsNotNone(expected)

        actual = getFileData(book)
        self.assertEqual(actual.getvalue(), expected.getvalue())

    def test_read_book_from_zip_file(self) -> None:
        book = self.setup_zipped_book(filename="539273.fb2", path="data/books.zip")
        expected = read_book_from_zip_file(
            os.path.join(config.SOPDS_ROOT_LIB, book.path), book.filename
        )
        self.assertIsNotNone(expected)

        actual = getFileData(book)
        self.assertEqual(actual.getvalue(), expected.getvalue())

    def test_read_book_from_inp_file(self) -> None:
        expected = read_book_from_zip_file(
            "opds_catalog/tests/data/books.zip", "539273.fb2"
        )
        self.assertIsNotNone(expected)

        book = Book(filename="539273.fb2", cat_type=3, path="data/inpx/inp/books.zip")
        actual = getFileData(book)
        self.assertEqual(actual.getvalue(), expected.getvalue())

    def test_read_absent_book(self) -> None:
        # Проверки чтения данных из несуществующих файлов
        book = Book(filename="263001.fb2", cat_type=0, path="data")
        actual = getFileData(book)
        self.assertIsNone(actual)

        book = Book(filename="539273.fb2", cat_type=1, path="data/books1.zip")
        actual = getFileData(book)
        self.assertIsNone(actual)

        book = Book(filename="559273.fb2", cat_type=1, path="data/books.zip")
        actual = getFileData(book)
        self.assertIsNone(actual)

        book = Book(filename="539273.fb2", cat_type=3, path="data/inpx/inp/books1.zip")
        actual = getFileData(book)
        self.assertIsNone(actual)

        book = Book(filename="559273.fb2", cat_type=3, path="data/inpx/inp/books.zip")
        actual = getFileData(book)
        self.assertIsNone(actual)


class TestGetFileDataZip(TestCase):
    def setUp(self) -> None:
        self.root_library = config.SOPDS_ROOT_LIB
        config.SOPDS_ROOT_LIB = "opds_catalog/tests/"

    def tearDown(self) -> None:
        config.SOPDS_ROOT_LIB = self.root_library

    def test_create_zip_stream(self) -> None:
        expected_file_name = "zip_book.fb2"
        expected_content = read_file_as_iobytes("opds_catalog/tests/data/262001.fb2")
        book = Book(
            title="zip book",
            format="fb2",
            filename="262001.fb2",
            cat_type=0,
            path="data",
        )

        actual = getFileDataZip(book)
        with zipfile.ZipFile(actual, "r") as tested:
            self.assertIn(expected_file_name, tested.namelist())
            actual_content = tested.read(expected_file_name)
            self.assertEqual(expected_content.getvalue(), actual_content)


class TestGetFsBookPath(TestCase):
    def setUp(self) -> None:
        self.root_library = config.SOPDS_ROOT_LIB
        config.SOPDS_ROOT_LIB = "opds_catalog/tests/"

    def tearDown(self) -> None:
        config.SOPDS_ROOT_LIB = self.root_library

    def test_inp_book_path(self) -> None:
        book = Book(filename="539273.fb2", cat_type=3, path="data/inpx/inp/books.zip")
        expected_path = "opds_catalog/tests/data/books.zip"
        actual_path = get_fs_book_path(book)
        self.assertEqual(actual_path, expected_path)

    def test_normal_book_path(self) -> None:
        book = Book(filename="539273.fb2", cat_type=0, path="data/books.zip")
        expected_path = "opds_catalog/tests/data/books.zip"
        actual_path = get_fs_book_path(book)
        self.assertIsNotNone(actual_path)
        self.assertEqual(actual_path, expected_path)


class TestGetFileDataConv(TestCase):
    def setUp(self) -> None:
        self.root_library = config.SOPDS_ROOT_LIB
        config.SOPDS_ROOT_LIB = "opds_catalog/tests/"

    def tearDown(self) -> None:
        config.SOPDS_ROOT_LIB = self.root_library

    def test_convert_non_fb2_book(self) -> None:
        book = Book(title="Not a fb2 book", format="pdf")
        actual = getFileDataConv(book, "epub")
        self.assertIsNone(actual)

    def test_convert_absent_book(self) -> None:
        book = Book(
            title="I'm not exists", filename="263001.fb2", cat_type="0", path="data"
        )
        actual = getFileDataConv(book, "epub")
        self.assertIsNone(actual)


#    def test_convert_to_epub(self):
#        book = Book(filename="539273.fb2", cat_type=1, path="data/books.zip")
#        actual = getFileDataConv(book, "epub")
#        self.assertIsNotNone(actual)


@pytest.fixture
def manage_sopds_root_lib():
    backup = config.SOPDS_ROOT_LIB
    config.SOPDS_ROOT_LIB = os.path.join(settings.BASE_DIR, "opds_catalog/tests/data/")
    yield config
    config.SOPDS_ROOT_LIB = backup


@pytest.fixture
def create_regular_book():
    book = create_book(filename="262001.fb2", cat_type=opdsdb.CAT_NORMAL, path=".")
    book.save()
    return book


@pytest.mark.django_db
def test_config_custom(manage_sopds_root_lib) -> None:
    conf = manage_sopds_root_lib
    assert conf.SOPDS_ROOT_LIB == os.path.join(
        settings.BASE_DIR, "opds_catalog/tests/data/"
    )


@pytest.mark.django_db
def test_get_book_cover(manage_sopds_root_lib, create_regular_book, client) -> None:
    book = create_regular_book
    url = reverse("opds:cover", args=(book.id,))
    actual = client.get(url)
    assert actual.status_code == 200
    assert actual["Content-Length"] == "56360"
