"""Тесты сервисов книг book_services."""

import pytest

from tests.fixtures.model_fixtures import (  # noqa: F401
    book_with_relations,
    catalog,
    test_datetime,
    update_counters,
    user,
)

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
