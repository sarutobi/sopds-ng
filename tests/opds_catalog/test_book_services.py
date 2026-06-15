"""Тесты сервисов книг book_services."""

import pytest

from opds_catalog.models import Book
from opds_catalog.services import book_services


pytestmark = pytest.mark.django_db


class TestBookServices:
    """Тесты методов book_services."""

    def test_search_book_by_exact_title(self, book_with_relations):
        """Поиск по точному названию."""
        results = book_services.search_book("b", "Книга", None, None)
        assert results.count() == 1
        assert results[0].title == "Книга"

    def test_search_book_by_begin_title(self, book_with_relations):
        """Поиск по началу названия."""
        results = book_services.search_book("m", "Кни", None, None)
        assert results.count() == 1

    def test_search_book_by_author(self, book_with_relations):
        """Поиск книг автора."""
        author = book_with_relations.authors.first()
        results = book_services.search_book("a", author.id, None, None)
        assert results.count() == 1

    def test_search_book_by_series(self, book_with_relations):
        """Поиск книг по серии."""
        series_obj = book_with_relations.series.first()
        results = book_services.search_book("s", series_obj.id, None, None)
        assert results.count() == 1

    def test_search_book_without_results(self):
        """Поиск несуществующей книги."""
        results = book_services.search_book("b", "Nonexist", None, None)
        assert results.count() == 0

    def test_book_description(self, book_with_relations):
        """Описание книги."""
        book_data = {
            "title": "Test Book",
            "annotation": "Test annotation",
            "authors": [{"full_name": "Author1"}],
            "series": [{"ser": "Series1", "ser_no": 1}],
            "ser_no": [],
            "genres": [{"subsection": "fantasy"}],
            "language": "ru",
            "filename": "testbook.fb2",
            "filesize": 500,
            "docdate": "01.01.2016",
        }
        desc = book_services.book_description(book_data)
        assert "Test annotation" in desc
        assert "Author1" in desc
        assert "Series1" in desc
        # ser_no block is skipped because list is empty; "1" not expected

    def test_paginated_book_content(self, book_with_relations):
        """Пагинация списка книг."""
        books = Book.objects.all()
        items, paginator = book_services.paginated_book_content(books, 1, True)
        assert len(items) == 1
        assert paginator.get_data_dict()["number"] == 1
        assert paginator.get_data_dict()["has_next"] is False

    def test_find_books_by_template_no_books(self):
        """Шаблон книг при пустой БД."""
        results = book_services.find_books_by_template("", 1, 0)
        assert len(results) == 0

    def test_find_books_by_template_with_lang_code(self, catalog):
        """Шаблон книг с фильтром по языку."""
        book = Book.objects.create(
            filename="test.fb2",
            path=".",
            format="fb2",
            cat_type=0,
            title="Test",
            search_title="TEST",
            lang_code=1,
            catalog=catalog,
        )
        results = book_services.find_books_by_template("T", 1, lang_code=1)
        assert len(results) > 0

    def test_search_book_by_genre(self, book_with_relations):
        """Поиск книг по жанру."""
        genre = book_with_relations.genres.first()
        results = book_services.search_book("g", str(genre.id), None, None)
        assert results.count() == 1

    def test_search_book_by_exact_title(self, book_with_relations):
        """Поиск по точному названию (type='e')."""
        book_with_relations.search_title = "КНИГА"
        book_with_relations.save()
        results = book_services.search_book("e", "КНИГА", None, None)
        assert results.count() == 1

    def test_search_book_unsupported_type(self):
        """Поиск с неподдерживаемым типом."""
        import pytest

        with pytest.raises(ValueError, match="is not supported"):
            book_services.search_book("x", "test", None, None)

    def test_find_book_doubles(self, book_with_relations, catalog):
        """Поиск дубликатов книги."""
        # Создаём книгу-дубликат
        book2 = Book.objects.create(
            filename="dup.fb2",
            path=".",
            format="fb2",
            cat_type=0,
            title="Книга",
            search_title="КНИГА",
            catalog=catalog,
        )
        author = book_with_relations.authors.first()
        from opds_catalog.models import bauthor

        bauthor.objects.create(book=book2, author=author)
        results = book_services.search_book(
            "d", str(book_with_relations.id), None, None
        )
        assert results.count() == 1

    def test_author_books_count(self, book_with_relations):
        """Подсчёт книг автора."""
        author = book_with_relations.authors.first()
        count = book_services.author_books_count(author)
        assert count == 1

    def test_author_books_count_by_int(self, book_with_relations):
        """Подсчёт книг автора по ID."""
        author = book_with_relations.authors.first()
        count = book_services.author_books_count(author.id)
        assert count == 1

    def test_book_description_with_ser_no(self, book_with_relations):
        """Описание книги с номером в серии."""
        book_data = {
            "title": "Test",
            "annotation": "Annot",
            "authors": [{"full_name": "Author1"}],
            "series": [{"ser": "Ser1"}],
            "ser_no": [{"ser_no": 1}],
            "genres": [{"subsection": "fantasy"}],
            "language": "ru",
            "filename": "test.fb2",
            "filesize": 500,
            "docdate": "01.01.2016",
        }
        desc = book_services.book_description(book_data)
        assert "Ser1" in desc
        assert "1" in desc
