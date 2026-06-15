"""Тесты getFileName — unit, без БД, только расчёт имени файла.

NOTE: @pytest.mark.override_config требует доступа к БД (constance хранит
значения в таблице), поэтому django_db обязателен, несмотря на unit-характер.
"""

import pytest

from opds_catalog.utils import getFileName

pytestmark = pytest.mark.django_db


@pytest.fixture
def _book(book_factory):
    """Создаёт книгу в памяти (без сохранения в БД)."""
    return book_factory(title="Книга", format="fb2", filename="123abc.zip")


@pytest.mark.override_config(SOPDS_TITLE_AS_FILENAME=False)
def test_by_filename(_book) -> None:
    """Имя файла из filename, если SOPDS_TITLE_AS_FILENAME=False."""
    expected = _book.filename
    result = getFileName(_book)
    assert result == expected


@pytest.mark.override_config(SOPDS_TITLE_AS_FILENAME=True)
def test_by_title(_book) -> None:
    """Имя файла из title, если SOPDS_TITLE_AS_FILENAME=True."""
    expected = "Kniga.fb2"
    result = getFileName(_book)
    assert result == expected


@pytest.mark.override_config(SOPDS_TITLE_AS_FILENAME=False)
def test_by_russian_filename(book_factory) -> None:
    """Имя файла транслитерируется, даже если filename на кириллице."""
    book = book_factory(title="Книга", format="fb2", filename="Книга.zip")
    expected = "Kniga.zip"
    result = getFileName(book)
    assert result == expected
