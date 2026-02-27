"""Фикстуры моделей opds_catalog"""

from opds_catalog.models import Genre, Book

import pytest


@pytest.fixture
def genre() -> Genre:
    """Жанр книги."""
    return Genre.objects.create(section="Section A", subsection="Subsection A1")


@pytest.fixture
def book(genre) -> Book:
    """Книга."""
    return Book.objects.create(title="Test title", genre=genre)
