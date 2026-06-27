"""Тесты моделей opds_catalog с использованием pytest."""

import pytest

from opds_catalog import models
from opds_catalog.models import (
    Counter,
    bauthor,
    bgenre,
    bookshelf,
    bseries,
)

pytestmark = pytest.mark.django_db


class TestBook:
    """Тесты модели Book."""

    def test_fields(self, book):
        """Проверка значений полей книги."""
        assert book.filename == "testbook.fb2"
        assert book.path == "."
        assert book.filesize == 500
        assert book.format == "fb2"
        assert book.cat_type == 0
        assert book.docdate == "01.01.2016"
        assert book.lang == "ru"
        assert book.title == "Книга"
        assert book.search_title == "КНИГА"
        assert book.annotation == "Аннотация"
        assert book.avail == 2
        assert book.catalog.path == "."
        assert book.catalog.cat_name == "."
        assert book.catalog.cat_type == 0

    def test_str(self, book):
        """__str__ возвращает название книги."""
        assert str(book) == "Книга"


class TestAuthor:
    """Тесты модели Author."""

    def test_author_relations(self, book_with_relations):
        """Связь книги с автором."""
        book = book_with_relations
        assert book.authors.count() == 1
        db_author = book.authors.get(full_name="Шелепнев Дмитрий")
        assert db_author.search_full_name == "ШЕЛЕПНЕВ ДМИТРИЙ"

    def test_bauthor_creation(self, book_with_relations, author):
        """Промежуточная таблица bauthor создана."""
        assert bauthor.objects.filter(book=book_with_relations, author=author).exists()


class TestGenre:
    """Тесты модели Genre."""

    def test_genre_relations(self, book_with_relations):
        """Связь книги с жанром."""
        book = book_with_relations
        assert book.genres.count() == 1
        db_genre = book.genres.get(genre="fantastic0")
        assert db_genre.section == "fantastic1"
        assert db_genre.subsection == "fantastic2"

    def test_bgenre_creation(self, book_with_relations, genre):
        """Промежуточная таблица bgenre создана."""
        assert bgenre.objects.filter(book=book_with_relations, genre=genre).exists()


class TestSeries:
    """Тесты модели Series."""

    def test_series_relations(self, book_with_relations):
        """Связь книги с серией."""
        book = book_with_relations
        assert book.series.count() == 1
        ser = book.series.all()[0]
        assert ser.ser == "mywork"
        assert ser.search_ser == "MYWORK"
        bseries_entry = bseries.objects.get(ser=ser)
        assert bseries_entry.ser_no == 1


class TestBookshelf:
    """Тесты модели bookshelf."""

    def test_bookshelf_creation(self, bookshelf_entry, user):
        """Запись на книжной полке создана и связана с пользователем."""
        assert bookshelf.objects.all().count() == 1
        assert bookshelf.objects.filter(user=user).count() == 1

    def test_bookshelf_multiple(self, book_with_relations, user, test_datetime):
        """Несколько записей для одного пользователя."""
        from opds_catalog.models import Book

        # Создаём первую запись на полке
        bookshelf.objects.create(
            user=user, book=book_with_relations, readtime=test_datetime
        )

        # Создаём вторую книгу
        second_book = Book.objects.create(
            filename="second.fb2",
            path=".",
            filesize=300,
            format="fb2",
            cat_type=0,
            registerdate=test_datetime,
            docdate="01.01.2016",
            lang="en",
            title="Second",
            search_title="SECOND",
            annotation="",
            avail=2,
            catalog=book_with_relations.catalog,
        )
        bookshelf.objects.create(user=user, book=second_book, readtime=test_datetime)
        assert bookshelf.objects.filter(user=user).count() == 2


class TestCounter:
    """Тесты менеджера CounterManager."""

    def test_initial_counters_zero(self):
        """До вызова update_known_counters счётчики возвращают 0."""
        assert Counter.objects.get_counter(models.counter_allbooks) == 0
        assert Counter.objects.get_counter(models.counter_allauthors) == 0
        assert Counter.objects.get_counter(models.counter_allcatalogs) == 0
        assert Counter.objects.get_counter(models.counter_allgenres) == 0
        assert Counter.objects.get_counter(models.counter_allseries) == 0

    def test_counters_after_update(self, book_with_relations, update_counters):
        """После обновления счётчики соответствуют количеству записей."""
        assert Counter.objects.get_counter(models.counter_allbooks) == 1
        assert Counter.objects.get_counter(models.counter_allauthors) == 1
        assert Counter.objects.get_counter(models.counter_allcatalogs) == 1
        assert Counter.objects.get_counter(models.counter_allgenres) == 1
        assert Counter.objects.get_counter(models.counter_allseries) == 1

    def test_get_lastscan_none(self):
        """Если счётчиков нет, get_lastscan возвращает None."""
        assert Counter.objects.get_lastscan() is None

    def test_get_lastscan_after_update(self, update_counters):
        """После обновления get_lastscan возвращает не None."""
        lastscan = Counter.objects.get_lastscan()
        assert lastscan is not None
