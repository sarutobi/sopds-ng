import os

from django.test import TestCase

from opds_catalog.fb2parse import fb2parser

class parserTestCase(TestCase):
    test_module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_ROOTLIB = os.path.join(test_module_path, 'tests/data')
    test_fb2 = "262001.fb2"
    test_bad_fb2 = "badfile.fb2"

    def setUp(self):
        pass

    def test_fb2parse_valid(self):
        """ Тестирование класса fb2parser - разбор валидного fb2 """
        parser = fb2parser()
        parser.reset()
        f = open(os.path.join(self.test_ROOTLIB, self.test_fb2), 'rb')
        parser.parse(f)
        self.assertEqual(parser.book_title.getvalue()[0], "The Sanctuary Sparrow")
        self.assertEqual(parser.author_first.getvalue()[0], "Ellis")
        self.assertEqual(parser.author_last.getvalue()[0], "Peters")
        self.assertEqual(parser.genre.getvalue()[0], "antique")
        self.assertEqual(parser.lang.getvalue()[0], "en")
        self.assertEqual(parser.docdate.getvalue()[0], "30.1.2011")
        self.assertEqual(parser.parse_error, 0)

    def test_fb2parse_novalid(self):
        """ Тестирование класса fb2parser - разбор невалидного fb2 """
        parser = fb2parser()
        parser.reset()
        f = open(os.path.join(self.test_ROOTLIB, self.test_bad_fb2), 'rb')
        parser.parse(f)
        self.assertNotEqual(parser.parse_error, 0)

    def test_fb2parse_cover(self):
        """ Тестирование класса fb2parser - извлечение обдложки из fb2 """
        parser = fb2parser(True)
        parser.reset()
        f = open(os.path.join(self.test_ROOTLIB, self.test_fb2), 'rb')
        parser.parse(f)
        self.assertEqual(parser.parse_error, 0)
        self.assertEqual(len(parser.cover_image.cover_data), 76207)
        self.assertEqual(parser.cover_image.getattr('content-type'), "image/jpeg")
