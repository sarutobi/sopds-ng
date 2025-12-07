import os

import pytest
from constance import config

from opds_catalog import opdsdb
from opds_catalog.models import Author, Book, Catalog, Genre, Series
from opds_catalog.sopdscan import opdsScanner


@pytest.mark.django_db
@pytest.mark.usefixtures("fake_sopds_root_lib")
class TestBookScaner(object):
    test_module_path = os.path.dirname(os.path.abspath(__file__))
    test_ROOTLIB = os.path.join(test_module_path, "data")
    test_fb2 = "262001.fb2"
    test_epub = "mirer.epub"
    test_mobi = "robin_cook.mobi"
    test_zip = "books.zip"

    @pytest.mark.parametrize("fb2sax", [True, False])
    def test_processfile_fb2(self, fb2sax):
        """Тестирование процедуры processfile (извлекает метаданные из книги FB2 и помещает в БД)"""
        config.SOPDS_FB2SAX = fb2sax
        opdsdb.clear_all()
        scanner = opdsScanner()
        scanner.processfile(
            self.test_fb2,
            self.test_ROOTLIB,
            os.path.join(self.test_ROOTLIB, self.test_fb2),
            None,
            0,
            495373,
        )
        book = Book.objects.get(filename=self.test_fb2)
        assert book is not None
        assert scanner.books_added == 1
        assert book.filename == self.test_fb2
        assert book.path == "."
        assert book.format == "fb2"
        assert book.cat_type == 0
        # self.assertGreaterEqual(book.registerdate, )
        assert book.docdate == "30.1.2011"
        assert book.lang == "en"
        assert book.title == "The Sanctuary Sparrow"
        assert book.search_title == "The Sanctuary Sparrow".upper()
        assert book.annotation == ""
        assert book.avail == 2
        assert book.catalog.path == "."
        assert book.catalog.cat_name == "."
        assert book.catalog.cat_type == 0
        assert book.filesize == 495373

        assert book.authors.count() == 1
        assert (
            book.authors.get(full_name="Peters Ellis").search_full_name
            == "PETERS ELLIS"
        )

        assert book.genres.count() == 1
        assert book.genres.get(genre="antique").section == opdsdb.unknown_genre
        assert book.genres.get(genre="antique").subsection == "antique"

    def test_processfile_epub(self):
        """Тестирование процедуры processfile (извлекает метаданные из книги EPUB и помещает в БД)"""
        opdsdb.clear_all()
        scanner = opdsScanner()
        scanner.processfile(
            self.test_epub,
            self.test_ROOTLIB,
            os.path.join(self.test_ROOTLIB, self.test_epub),
            None,
            0,
            491279,
        )
        book = Book.objects.get(filename=self.test_epub)
        assert book is not None
        assert scanner.books_added == 1
        assert book.filename == self.test_epub
        assert book.path == "."
        assert book.format == "epub"
        assert book.cat_type == 0
        # assertGreater book.registerdate== )
        assert book.docdate == "2015"
        assert book.lang == "ru"
        assert book.title == "У меня девять жизней (шф (продолжатели))"
        assert book.search_title == "У меня девять жизней (шф (продолжатели))".upper()

        assert book.annotation == "Собрание произведений. Том 2"
        assert book.avail == 2
        assert book.catalog.path == "."
        assert book.catalog.cat_name == "."
        assert book.catalog.cat_type == 0
        assert book.filesize == 491279

        assert book.authors.count() == 1
        assert (
            book.authors.get(full_name="Мирер Александр").search_full_name
            == "МИРЕР АЛЕКСАНДР"
        )

        assert book.genres.count() == 1
        assert book.genres.get(genre="sf").section == opdsdb.unknown_genre
        assert book.genres.get(genre="sf").subsection == "sf"

    def test_processfile_mobi(self):
        """Тестирование процедуры processfile (извлекает метаданные из книги EPUB и помещает в БД)"""
        opdsdb.clear_all()
        scanner = opdsScanner()
        scanner.processfile(
            self.test_mobi,
            self.test_ROOTLIB,
            os.path.join(self.test_ROOTLIB, self.test_mobi),
            None,
            0,
            542811,
        )
        book = Book.objects.get(filename=self.test_mobi)
        assert book is not None
        assert scanner.books_added == 1
        assert book.filename == self.test_mobi
        assert book.path == "."
        assert book.format == "mobi"
        assert book.cat_type == 0
        # self.assertGreaterEqual(book.registerdate ==
        assert book.docdate == "2011-11-20"
        assert book.lang == ""
        assert book.title == "Vector"
        assert book.search_title == "Vector".upper()
        assert book.annotation == ""
        assert book.avail == 2
        assert book.catalog.path == "."
        assert book.catalog.cat_name == "."
        assert book.catalog.cat_type == 0
        assert book.filesize == 542811

        assert book.authors.count() == 1
        assert book.authors.get(full_name="Cook Robin").search_full_name == "COOK ROBIN"

    def test_processzip(self):
        """Тестирование процедуры processzip (извлекает метаданные из книг, помещенных в архив и помещает их БД)"""
        opdsdb.clear_all()
        scanner = opdsScanner()
        scanner.processzip(
            self.test_zip,
            self.test_ROOTLIB,
            os.path.join(self.test_ROOTLIB, self.test_zip),
        )
        assert scanner.books_added == 3
        assert Book.objects.all().count() == 3
        assert Catalog.objects.all().count() == 2

        book = Book.objects.get(filename="539603.fb2")
        assert book.filesize == 15194
        assert book.path == self.test_zip
        assert book.cat_type == 1
        assert book.catalog.path == self.test_zip
        assert book.catalog.cat_name == self.test_zip
        assert book.catalog.cat_type == 1
        assert book.docdate == "2014-09-15"
        assert book.title == "Любовь в жизни Обломова"
        assert book.avail == 2
        assert book.authors.count() == 1
        assert (
            book.authors.get(full_name="Логинов Святослав").search_full_name
            == "ЛОГИНОВ СВЯТОСЛАВ"
        )

        assert book.genres.count() == 1
        assert book.genres.get(genre="nonf_criticism").section == opdsdb.unknown_genre

        assert book.genres.get(genre="nonf_criticism").subsection == "nonf_criticism"

        book = Book.objects.get(filename="539485.fb2")
        assert book.filesize == 12293
        assert book.path == self.test_zip
        assert book.cat_type == 1
        assert book.title == "Китайски сладкиш с късметче"
        assert book.authors.get(full_name="Фрич Чарлз").search_full_name == "ФРИЧ ЧАРЛЗ"

        book = Book.objects.get(filename="539273.fb2")
        assert book.filesize == 21722
        assert book.path == self.test_zip
        assert book.cat_type == 1
        assert book.title == "Драконьи Услуги"
        assert (
            book.authors.get(full_name="Куприянов Денис").search_full_name
            == "КУПРИЯНОВ ДЕНИС"
        )

    def test_scanall(self):
        """Тестирование процедуры scanall (извлекает метаданные из книг и помещает в БД)"""
        opdsdb.clear_all()
        scanner = opdsScanner()
        scanner.scan_all()
        assert scanner.books_added == 7
        assert scanner.bad_books == 3
        assert Book.objects.all().count() == 7
        assert Author.objects.all().count() == 6
        assert Genre.objects.all().count() == 5
        assert Series.objects.all().count() == 1
        assert Catalog.objects.all().count() == 4
