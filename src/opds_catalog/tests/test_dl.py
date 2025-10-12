# -*- coding: utf-8 -*-

from constance import config
from django.test import TestCase

from opds_catalog.dl import getFileName
from opds_catalog.models import Book


class DownloadsTestCase(TestCase):
    fixtures = ["testdb.json"]

    def setUp(self):
        pass

    def test_download_book(self):
        pass

    def test_download_zip(self):
        pass

    def test_download_cover(self):
        pass


class TestGetFileName(TestCase):
    def setUp(self) -> None:
        self.book = Book(title="Книга", format="fb2", filename="123abc.zip")
        self.title_as_filename = config.SOPDS_TITLE_AS_FILENAME

    def tearDown(self) -> None:
        config.SOPDS_TITLE_AS_FILENAME = self.title_as_filename

    def test_by_filename(self) -> None:
        expected_filename = self.book.filename
        config.SOPDS_TITLE_AS_FILENAME = False

        test_filename = getFileName(self.book)
        assert test_filename == expected_filename

    def test_by_title(self) -> None:
        config.SOPDS_TITLE_AS_FILENAME = True
        expected_filename = "Kniga.fb2"

        test_filename = getFileName(self.book)
        assert test_filename == expected_filename

    def test_by_russian_filename(self) -> None:
        book = Book(title="Книга", format="fb2", filename="Книга.zip")
        config.SOPDS_TITLE_AS_FILENAME = False
        expected_filename = "Kniga.zip"

        test_filename = getFileName(book)
        assert test_filename == expected_filename
