import pytest

from opds_catalog import constants
from opds_catalog.db_utils import clear_all, clear_genres
from opds_catalog.models import Catalog, Genre, bseries
from opds_catalog.services import scanner

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _opdsdb_setup():
    """Создаёт тестовое дерево каталогов, книгу, автора, жанр, серию."""
    clear_all()
    scanner.addcattree("root/child/subchild", constants.CAT_NORMAL)
    book = scanner.addbook(
        "testbook.fb2",
        "root/child",
        scanner.findcat("root/child"),
        ".fb2",
        "Test Book",
        "Annotation",
        "01.01.2016",
        "ru",
        500,
        0,
    )
    scanner.addbauthor(book, scanner.addauthor("Test Author"))
    scanner.addbgenre(book, scanner.addgenre("fantastic"))
    scanner.addbseries(book, scanner.addseries("mywork"), 1)


class TestOpdsDb:  # integration
    """Тесты функций opdsdb (работа с БД: каталоги, книги, авторы, жанры)."""

    def test_cat_fn(self) -> None:
        """Тестирование функций addcattree, findcat"""
        assert Catalog.objects.filter(parent=None).count() == 1
        assert Catalog.objects.all().count() == 4

        cat = Catalog.objects.get(parent=None)
        assert cat.cat_name == "."
        cat = Catalog.objects.get(parent=cat)
        assert cat.cat_name == "root"
        cat = Catalog.objects.get(parent=cat)
        assert cat.cat_name == "child"
        cat = Catalog.objects.get(parent=cat)
        assert cat.cat_name == "subchild"

        cat = scanner.findcat("root/child")
        assert cat.cat_name == "child"
        assert cat.path == "root/child"
        assert cat.parent.cat_name == "root"
        assert cat.parent.parent.cat_name == "."
        assert cat.parent.parent.parent is None

    def test_book_fn(self) -> None:
        """Тестирование функций addbook, findbook"""
        book = scanner.findbook("testbook.fb2", "root/child")
        assert book is not None
        assert book.filename == "testbook.fb2"
        assert book.path == "root/child"
        assert book.catalog.cat_name == "child"
        assert book.catalog.cat_type == 0
        assert book.format == ".fb2"
        assert book.title == "Test Book"
        assert book.annotation == "Annotation"
        assert book.docdate == "01.01.2016"
        assert book.lang == "ru"
        assert book.filesize == 500
        assert book.cat_type == 0

    def test_author_fn(self) -> None:
        """Тестирование функций addauthor, addbauthor"""
        book = scanner.findbook("testbook.fb2", "root/child")
        assert book.authors.count() == 1
        assert (
            book.authors.get(full_name="Test Author").search_full_name == "TEST AUTHOR"
        )

    def test_genre_fn(self) -> None:
        """Тестирование функций addgenre, addbgenre"""
        book = scanner.findbook("testbook.fb2", "root/child")
        assert book.genres.count() == 1
        assert book.genres.get(genre="fantastic").section == "Unknown genre"
        assert book.genres.get(genre="fantastic").subsection == "fantastic"

    def test_series_fn(self) -> None:
        """Тестирование функций addseries, addbseries"""
        book = scanner.findbook("testbook.fb2", "root/child")
        assert book.series.count() == 1
        ser = book.series.all()[0]
        assert ser.ser == "mywork"
        assert bseries.objects.get(ser=ser).ser_no == 1

    def test_clear_genres(self) -> None:
        """Тестирование clear_genres"""
        assert Genre.objects.count() > 0
        # Сначала удаляем связи bgenre, чтобы избежать FK violation
        from opds_catalog.models import bgenre

        bgenre.objects.all().delete()
        clear_genres()
        assert Genre.objects.count() == 0

    def test_findbook_with_setavail(self) -> None:
        """Тестирование findbook с параметром setavail"""
        book = scanner.findbook("testbook.fb2", "root/child", setavail=1)
        assert book is not None
        assert book.avail == 2

    def test_findbook_not_found(self) -> None:
        """Тестирование findbook для несуществующей книги"""
        book = scanner.findbook("nonexist.fb2", "root/child")
        assert book is None

    def test_findcat_not_found(self) -> None:
        """Тестирование findcat для несуществующего каталога"""
        cat = scanner.findcat("nonexistent/path")
        assert cat is None

    def test_addcattree_existing(self) -> None:
        """Тестирование addcattree для уже существующего каталога"""
        cat = scanner.addcattree("root/child", constants.CAT_NORMAL)
        assert cat is not None
        assert cat.cat_name == "child"

    def test_addcattree_root(self) -> None:
        """Тестирование addcattree для корневого каталога"""
        cat = scanner.addcattree(".", 0)
        assert cat is not None
        assert cat.cat_name == "."

    def test_findauthor(self) -> None:
        """Тестирование findauthor"""
        authors = scanner.findauthor("Test Author")
        assert len(authors) == 1

    def test_findauthor_not_found(self) -> None:
        """Тестирование findauthor для несуществующего автора"""
        authors = scanner.findauthor("Nonexistent Author")
        assert len(authors) == 0

    def test_getlangcode(self) -> None:
        """Тестирование getlangcode"""
        from opds_catalog.utils import getlangcode

        assert getlangcode("") == 9  # empty
        assert getlangcode("Привет") == 1  # cyrillic
        assert getlangcode("Hello") == 2  # latin
        assert getlangcode("123") == 3  # digits

    def test_langcode_labels(self) -> None:
        """Тестирование меток LangCode (IntegerChoices)."""
        from opds_catalog.models import LangCode

        assert LangCode.CYRILLIC.label == "Кириллица"
        assert LangCode.LATIN.label == "Латиница"
        assert LangCode.DIGITS.label == "Цифры"
        assert LangCode.OTHER.label == "Другое"

    def test_langcode_validation(self) -> None:
        """Тестирование валидации lang_code в моделях."""
        from django.core.exceptions import ValidationError

        from opds_catalog.models import Book

        # Создаем книгу с некорректным кодом языка
        book = Book(title="Test", filename="test.fb2", path=".", lang_code=42)
        with pytest.raises(ValidationError) as excinfo:
            book.full_clean()

        # Проверяем, что ошибка относится именно к полю lang_code
        assert "lang_code" in excinfo.value.message_dict

    def test_p_function(self) -> None:
        """Тестирование функции p (обрезание 4-байтовых UTF)"""
        from opds_catalog.utils import p

        assert p("hello", 3) == "hel"
        assert p("", 3) == ""
        # 4-byte unicode char should be stripped
        assert p("a\U00010000b", 10) == "ab"

    def test_avail_check_prepare(self) -> None:
        """Тестирование avail_check_prepare"""
        scanner.avail_check_prepare()
        book = scanner.findbook("testbook.fb2", "root/child")
        assert book.avail == 1

    def test_arc_skip_unchanged(self) -> None:
        """Тестирование arc_skip с неизменённым архивом"""
        cat = scanner.findcat("root/child")
        cat.cat_size = 100
        cat.save()
        result = scanner.archive_skip("root/child", 100, depth=0)
        assert result == 1

    def test_arc_skip_nonexistent(self) -> None:
        """Тестирование arc_skip с несуществующим каталогом"""
        result = scanner.archive_skip("nonexistent", 100, depth=0)
        assert result == 0

    def test_arc_skip_changed(self) -> None:
        """Тестирование arc_skip с изменённым архивом"""
        cat = scanner.findcat("root/child")
        cat.cat_size = 100
        cat.save()
        result = scanner.archive_skip("root/child", 200, depth=0)
        assert result == 0

    def test_inp_skip_unchanged(self) -> None:
        """Тестирование inp_skip — возвращает 0, если нет дочерних книг."""
        subchild_cat = scanner.findcat("root/child/subchild")
        subchild_cat.cat_type = constants.CAT_INP
        subchild_cat.cat_size = 100
        subchild_cat.save()
        result = scanner.archive_skip("root/child/subchild", 100, depth=1)
        assert result == 0

    def test_inp_skip_nonexistent(self) -> None:
        """Тестирование inp_skip с несуществующим каталогом"""
        result = scanner.archive_skip("nonexistent", 100, depth=1)
        assert result == 0

    def test_inpx_skip_unchanged(self) -> None:
        """Тестирование inpx_skip с неизменённым файлом"""
        result = scanner.archive_skip("root/child/subchild", 100, depth=2)
        assert result == 0

    def test_inpx_skip_nonexistent(self) -> None:
        """Тестирование inpx_skip с несуществующим каталогом"""
        result = scanner.archive_skip("nonexistent", 100, depth=2)
        assert result == 0
