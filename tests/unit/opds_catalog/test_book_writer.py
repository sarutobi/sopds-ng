"""Юнит-тесты для BookWriter."""

import pytest

from opds_catalog.models import Author, Book, Catalog, Genre, Series
from opds_catalog.services.book_writer import BookWriter, FileSpec
from opds_catalog.services.dto import AuthorMetadata, BookMetadata, SeriesMetadata


@pytest.mark.django_db
def test_book_writer_basic_save(db):
    """Проверка базового сохранения книги и создания связей."""
    writer = BookWriter()

    meta = BookMetadata(
        title="Test Book",
        authors=[AuthorMetadata(full_name="Author 1")],
        genres=["Genre 1"],
        series=[SeriesMetadata(name="Series 1")],
    )

    file_spec = FileSpec(
        path="/lib",
        filename="book.fb2",
        rel_path="books/book.fb2",
        extension="fb2",
        file_size=1024,
    )

    catalog = Catalog.objects.create(path="/lib", cat_size=100)

    outcome = writer.save_book(meta, file=file_spec, catalog=catalog, cat_type=1)

    assert outcome.created is True
    assert Book.objects.count() == 1
    assert Author.objects.count() == 1
    assert Genre.objects.count() == 1
    assert Series.objects.count() == 1
    assert outcome.authors_linked == 1
    assert outcome.genres_linked == 1
    assert outcome.series_linked == 1


@pytest.mark.django_db
def test_book_writer_idempotency(db):
    """Проверка идемпотентности: повторное сохранение не создает дублей."""
    writer = BookWriter()

    meta = BookMetadata(
        title="Test Book",
        authors=[AuthorMetadata(full_name="Author 1")],
        genres=["Genre 1"],
        series=[SeriesMetadata(name="Series 1")],
    )

    file_spec = FileSpec(
        path="/lib",
        filename="book.fb2",
        rel_path="books/book.fb2",
        extension="fb2",
        file_size=1024,
    )

    catalog = Catalog.objects.create(path="/lib", cat_size=100)

    # Первый прогон
    outcome1 = writer.save_book(meta, file=file_spec, catalog=catalog, cat_type=1)
    assert outcome1.created is True

    # Второй прогон
    outcome2 = writer.save_book(meta, file=file_spec, catalog=catalog, cat_type=1)
    assert outcome2.created is False
    assert Book.objects.count() == 1
