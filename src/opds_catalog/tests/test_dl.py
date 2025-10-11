# -*- coding: utf-8 -*-

from django.conf import settings
from django.test import TestCase, Client, override_settings

from opds_catalog.dl import getFileName
from opds_catalog.models import Book


class DownloadsTestCase(TestCase):
    fixtures = ['testdb.json']

    def setUp(self):
        pass

    def test_download_book(self):
        pass

    def test_download_zip(self):
        pass
 
    def test_download_cover(self):
        pass

class TestGetFileName(TestCase):

    def setUp(self):
        self.book = Book(title="Книга", format="fb2", filename="123abc.zip")
        self.constance = settings.CONSTANCE_CONFIG

    def test_by_filename(self):
        self.constance['SOPDS_TITLE_AS_FILENAME'] = (False, '')
        expected_filename = self.book.filename

        with override_settings(CONSTANCE_CONFIG = self.constance):
            test_filename = getFileName(self.book)
            assert test_filename == expected_filename

    def test_by_title(self):
        self.constance['SOPDS_TITLE_AS_FILENAME'] = (True, '')
        expected_filename = 'Kniga.fb2'

        with override_settings(CONSTANCE_CONFIG = self.constance):
            test_filename = getFileName(self.book)
            assert test_filename == expected_filename

    def test_by_russian_filename(self):
        self.constance['SOPDS_TITLE_AS_FILENAME'] = (False, '')
        book = Book(title="Книга", format="fb2", filename="Книга.zip")
        expected_filename = "Kniga.zip"

        with override_settings(CONSTANCE_CONFIG = self.constance):
            test_filename = getFileName(book)
            assert test_filename == expected_filename

