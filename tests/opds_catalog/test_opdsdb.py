from django.test import TestCase

from opds_catalog.models import Catalog, Genre, bseries
from src.opds_catalog import opdsdb


class opdsdbTestCase(TestCase):
    def setUp(self):
        opdsdb.clear_all()
        opdsdb.addcattree("root/child/subchild", opdsdb.CAT_NORMAL)
        book = opdsdb.addbook(
            "testbook.fb2",
            "root/child",
            opdsdb.findcat("root/child"),
            ".fb2",
            "Test Book",
            "Annotation",
            "01.01.2016",
            "ru",
            500,
            0,
        )
        opdsdb.addbauthor(book, opdsdb.addauthor("Test Author"))
        opdsdb.addbgenre(book, opdsdb.addgenre("fantastic"))
        opdsdb.addbseries(book, opdsdb.addseries("mywork"), 1)

    def test_cat_fn(self):
        """Тестирование функций addcattree, findcat"""
        self.assertEqual(Catalog.objects.filter(parent=None).count(), 1)
        self.assertEqual(Catalog.objects.all().count(), 4)

        cat = Catalog.objects.get(parent=None)
        self.assertEqual(cat.cat_name, ".")
        cat = Catalog.objects.get(parent=cat)
        self.assertEqual(cat.cat_name, "root")
        cat = Catalog.objects.get(parent=cat)
        self.assertEqual(cat.cat_name, "child")
        cat = Catalog.objects.get(parent=cat)
        self.assertEqual(cat.cat_name, "subchild")

        cat = opdsdb.findcat("root/child")
        self.assertEqual(cat.cat_name, "child")
        self.assertEqual(cat.path, "root/child")
        self.assertEqual(cat.parent.cat_name, "root")
        self.assertEqual(cat.parent.parent.cat_name, ".")
        self.assertIsNone(cat.parent.parent.parent)

    def test_book_fn(self):
        """Тестирование функций addbook, findbook"""
        book = opdsdb.findbook("testbook.fb2", "root/child")
        self.assertIsNotNone(book)
        self.assertEqual(book.filename, "testbook.fb2")
        self.assertEqual(book.path, "root/child")
        self.assertEqual(book.catalog.cat_name, "child")
        self.assertEqual(book.catalog.cat_type, 0)
        self.assertEqual(book.format, ".fb2")
        self.assertEqual(book.title, "Test Book")
        self.assertEqual(book.annotation, "Annotation")
        self.assertEqual(book.docdate, "01.01.2016")
        self.assertEqual(book.lang, "ru")
        self.assertEqual(book.filesize, 500)
        self.assertEqual(book.cat_type, 0)

    def test_author_fn(self):
        """Тестирование функций addauthor, addbauthor"""
        book = opdsdb.findbook("testbook.fb2", "root/child")
        self.assertEqual(book.authors.count(), 1)
        self.assertEqual(
            book.authors.get(full_name="Test Author").search_full_name, "TEST AUTHOR"
        )

    def test_genre_fn(self):
        """Тестирование функций addgenre, addbgenre"""
        book = opdsdb.findbook("testbook.fb2", "root/child")
        self.assertEqual(book.genres.count(), 1)
        self.assertEqual(
            book.genres.get(genre="fantastic").section, opdsdb.unknown_genre
        )
        self.assertEqual(book.genres.get(genre="fantastic").subsection, "fantastic")

    def test_series_fn(self):
        """Тестирование функций addseries, addbseries"""
        book = opdsdb.findbook("testbook.fb2", "root/child")
        self.assertEqual(book.series.count(), 1)
        ser = book.series.all()[0]
        self.assertEqual(ser.ser, "mywork")
        self.assertEqual(bseries.objects.get(ser=ser).ser_no, 1)

    def test_clear_genres(self):
        """Тестирование clear_genres"""
        self.assertGreater(Genre.objects.count(), 0)
        # Сначала удаляем связи bgenre, чтобы избежать FK violation
        from opds_catalog.models import bgenre

        bgenre.objects.all().delete()
        opdsdb.clear_genres()
        self.assertEqual(Genre.objects.count(), 0)

    def test_findbook_with_setavail(self):
        """Тестирование findbook с параметром setavail"""
        book = opdsdb.findbook("testbook.fb2", "root/child", setavail=1)
        self.assertIsNotNone(book)
        self.assertEqual(book.avail, 2)

    def test_findbook_not_found(self):
        """Тестирование findbook для несуществующей книги"""
        book = opdsdb.findbook("nonexist.fb2", "root/child")
        self.assertIsNone(book)

    def test_findcat_not_found(self):
        """Тестирование findcat для несуществующего каталога"""
        cat = opdsdb.findcat("nonexistent/path")
        self.assertIsNone(cat)

    def test_addcattree_existing(self):
        """Тестирование addcattree для уже существующего каталога"""
        cat = opdsdb.addcattree("root/child", opdsdb.CAT_NORMAL)
        self.assertIsNotNone(cat)
        self.assertEqual(cat.cat_name, "child")

    def test_addcattree_root(self):
        """Тестирование addcattree для корневого каталога"""
        cat = opdsdb.addcattree(".", 0)
        self.assertIsNotNone(cat)
        self.assertEqual(cat.cat_name, ".")

    def test_findauthor(self):
        """Тестирование findauthor"""
        authors = opdsdb.findauthor("Test Author")
        self.assertEqual(len(authors), 1)

    def test_findauthor_not_found(self):
        """Тестирование findauthor для несуществующего автора"""
        authors = opdsdb.findauthor("Nonexistent Author")
        self.assertEqual(len(authors), 0)

    def test_getlangcode(self):
        """Тестирование getlangcode"""
        self.assertEqual(opdsdb.getlangcode(""), 9)  # empty
        self.assertEqual(opdsdb.getlangcode("Привет"), 1)  # cyrillic
        self.assertEqual(opdsdb.getlangcode("Hello"), 2)  # latin
        self.assertEqual(opdsdb.getlangcode("123"), 3)  # digits

    def test_p_function(self):
        """Тестирование функции p (обрезание 4-байтовых UTF)"""
        self.assertEqual(opdsdb.p("hello", 3), "hel")
        self.assertEqual(opdsdb.p("", 3), "")
        # 4-byte unicode char should be stripped
        self.assertEqual(opdsdb.p("a\U00010000b", 10), "ab")

    def test_avail_check_prepare(self):
        """Тестирование avail_check_prepare"""
        opdsdb.avail_check_prepare()
        book = opdsdb.findbook("testbook.fb2", "root/child")
        self.assertEqual(book.avail, 1)

    def test_arc_skip_unchanged(self):
        """Тестирование arc_skip с неизменённым архивом"""
        # Сначала создаём каталог с размером
        cat = opdsdb.findcat("root/child")
        cat.cat_size = 100
        cat.save()
        result = opdsdb.arc_skip("root/child", 100)
        self.assertEqual(result, 1)

    def test_arc_skip_nonexistent(self):
        """Тестирование arc_skip с несуществующим каталогом"""
        result = opdsdb.arc_skip("nonexistent", 100)
        self.assertEqual(result, 0)

    def test_arc_skip_changed(self):
        """Тестирование arc_skip с изменённым архивом"""
        cat = opdsdb.findcat("root/child")
        cat.cat_size = 100
        cat.save()
        result = opdsdb.arc_skip("root/child", 200)
        self.assertEqual(result, 0)

    def test_inp_skip_unchanged(self):
        """Тестирование inp_skip — возвращает 0, если нет дочерних книг."""
        subchild_cat = opdsdb.findcat("root/child/subchild")
        subchild_cat.cat_type = opdsdb.CAT_INP
        subchild_cat.cat_size = 100
        subchild_cat.save()
        # inp_skip ищет книги в дочерних каталогах от arcpath.
        # Наша книга в самом subchild, не в дочернем — возвращается 0
        result = opdsdb.inp_skip("root/child/subchild", 100)
        self.assertEqual(result, 0)

    def test_inp_skip_nonexistent(self):
        """Тестирование inp_skip с несуществующим каталогом"""
        result = opdsdb.inp_skip("nonexistent", 100)
        self.assertEqual(result, 0)

    def test_inpx_skip_unchanged(self):
        """Тестирование inpx_skip с неизменённым файлом"""
        result = opdsdb.inpx_skip("root/child/subchild", 100)
        self.assertEqual(result, 0)  # Нет parent->parent->parent

    def test_inpx_skip_nonexistent(self):
        """Тестирование inpx_skip с несуществующим каталогом"""
        result = opdsdb.inpx_skip("nonexistent", 100)
        self.assertEqual(result, 0)
