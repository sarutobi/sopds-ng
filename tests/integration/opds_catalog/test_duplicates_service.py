"""Тесты для DuplicatesService.

Сервис определения дубликатов книг. Единая точка логики,
которая в дальнейшем может быть вынесена в плагин.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User

from opds_catalog.models import Author, Book, Catalog, bauthor
from opds_catalog.services.duplicates_service import DuplicatesService

pytestmark = pytest.mark.django_db


# --- Вспомогательные фикстуры ---


@pytest.fixture
def catalog(db):
    """Простой корневой каталог для тестов."""
    return Catalog.objects.create(cat_name="root", path="/root")


@pytest.fixture
def minimal_catalog(db):
    """Корневой каталог для тестов сигнатуры (может быть None у тестов)."""
    return Catalog.objects.create(cat_name="root", path="/root")


def _make_book(
    title: str,
    lang: str = "ru",
    author_names: list[str] | None = None,
    catalog: Catalog | None = None,
) -> Book:
    """Создаёт книгу с указанными параметрами."""
    if catalog is None:
        catalog = Catalog.objects.create(cat_name="root", path="/root")
    book = Book.objects.create(
        title=title,
        search_title=title.upper(),
        lang=lang,
        catalog=catalog,
        filename=f"{title}.fb2",
        path=f"/root/{title}.fb2",
        docdate="2020-01-01",
    )
    if author_names:
        for name in author_names:
            author = Author.objects.create(
                full_name=name, search_full_name=name.upper()
            )
            bauthor.objects.create(book=book, author=author)
    return book


# --- _make_signature ---


class TestMakeSignature:
    """Тесты формирования сигнатуры книги."""

    def test_signature_includes_title(self):
        """Сигнатура содержит нормализованное название."""
        book = _make_book("Война и мир")
        sig = DuplicatesService._make_signature(book)
        assert "война и мир" in sig

    def test_signature_normalizes_case_and_whitespace(self):
        """Сигнатура приводит к lowercase и убирает пробелы по краям."""
        b1 = _make_book("Война и мир")
        b2 = _make_book("  Война и мир  ")
        assert DuplicatesService._make_signature(
            b1
        ) == DuplicatesService._make_signature(b2)

    def test_signature_includes_language(self):
        """Сигнатура содержит язык — разные языки дают разные сигнатуры."""
        b_ru = _make_book("Book", lang="ru")
        b_en = _make_book("Book", lang="en")
        assert DuplicatesService._make_signature(
            b_ru
        ) != DuplicatesService._make_signature(b_en)

    def test_signature_author_order_independent(self):
        """Порядок авторов не влияет на сигнатуру."""
        b1 = _make_book("Title", author_names=["Толкин", "Льюис"])
        b2 = _make_book("Title", author_names=["Льюис", "Толкин"])
        assert DuplicatesService._make_signature(
            b1
        ) == DuplicatesService._make_signature(b2)

    def test_signature_without_authors(self):
        """Книга без авторов формирует валидную сигнатуру."""
        book = _make_book("Анонимная книга")
        sig = DuplicatesService._make_signature(book)
        assert sig  # не пустая


# --- find_doubles_for_book ---


class TestFindDoublesForBook:
    """Тесты поиска дубликатов одной книги."""

    def test_finds_exact_double(self, catalog):
        """Находит книгу с таким же названием и авторами."""
        b1 = _make_book("Война и мир", author_names=["Толстой"], catalog=catalog)
        b2 = _make_book("Война и мир", author_names=["Толстой"], catalog=catalog)

        doubles = DuplicatesService.find_doubles_for_book(b1.id)

        assert b2 in doubles
        assert b1 not in doubles

    def test_does_not_match_different_authors(self, catalog):
        """Не считает дублями книги с разным составом авторов."""
        b1 = _make_book("Война и мир", author_names=["Толстой"], catalog=catalog)
        _make_book("Война и мир", author_names=["Другой автор"], catalog=catalog)

        doubles = DuplicatesService.find_doubles_for_book(b1.id)
        assert doubles.count() == 0

    def test_does_not_match_different_language(self, catalog):
        """Книги на разных языках не считаются дублями."""
        b_ru = _make_book(
            "War and Peace", lang="ru", author_names=["Tolstoy"], catalog=catalog
        )
        _make_book(
            "War and Peace", lang="en", author_names=["Tolstoy"], catalog=catalog
        )

        doubles = DuplicatesService.find_doubles_for_book(b_ru.id)
        assert doubles.count() == 0

    def test_returns_empty_when_no_doubles(self, catalog):
        """Если дублей нет — возвращается пустой QuerySet."""
        b1 = _make_book("Уникальная книга", catalog=catalog)

        doubles = DuplicatesService.find_doubles_for_book(b1.id)
        assert doubles.count() == 0

    def test_nonexistent_book_returns_empty(self):
        """Несуществующий book_id не вызывает ошибку."""
        doubles = DuplicatesService.find_doubles_for_book(99999)
        assert doubles.count() == 0


# --- find_all_duplicates ---


class TestFindFirstDoubleIds:
    """Тесты массового поиска id первого дубля."""

    def test_returns_empty_for_empty_input(self):
        """Пустой список возвращает пустой словарь."""
        assert DuplicatesService.find_first_double_ids([]) == {}

    def test_finds_double_for_each_book(self, catalog):
        """Для каждой книги с дублем возвращается id первого дубля из БД."""
        # Группа 1: "Война и мир" — две книги
        b1 = _make_book("Война и мир", author_names=["Толстой"], catalog=catalog)
        b2 = _make_book("Война и мир", author_names=["Толстой"], catalog=catalog)
        # Одиночная книга
        b_single = _make_book("Уникальная", catalog=catalog)

        result = DuplicatesService.find_first_double_ids([b1.id, b_single.id])

        assert result.get(b1.id) == b2.id
        assert b_single.id not in result

    def test_different_languages_have_no_doubles(self, catalog):
        """Книги на разных языках не имеют дублей в результате."""
        b_ru = _make_book("Title", lang="ru", author_names=["Author"], catalog=catalog)
        b_en = _make_book("Title", lang="en", author_names=["Author"], catalog=catalog)

        result = DuplicatesService.find_first_double_ids([b_ru.id, b_en.id])

        assert result == {}

    def test_nonexistent_ids_are_skipped(self, catalog):
        """Несуществующие id просто пропускаются."""
        b1 = _make_book("Книга", author_names=["Автор"], catalog=catalog)

        result = DuplicatesService.find_first_double_ids([b1.id, 99999])

        assert 99999 not in result


# --- find_all_duplicates ---


class TestFindAllDuplicates:
    """Тесты поиска дубликатов по всей коллекции."""

    def test_finds_groups(self, catalog):
        """Находит группы дублей во всей коллекции."""
        # Группа 1: 3 издания "Война и мир" Толстого
        _make_book("Война и мир", author_names=["Толстой"], catalog=catalog)
        _make_book("Война и мир", author_names=["Толстой"], catalog=catalog)
        b1 = _make_book("Война и мир", author_names=["Толстой"], catalog=catalog)

        # Одиночная книга
        _make_book("Уникальная", catalog=catalog)

        result = DuplicatesService.find_all_duplicates()

        assert b1.id in result
        doubles = list(result[b1.id])
        assert len(doubles) == 2

    def test_excludes_single_books(self, catalog):
        """Книги без дублей не попадают в результат."""
        b = _make_book("Одиночная", catalog=catalog)

        result = DuplicatesService.find_all_duplicates()

        assert b.id not in result

    def test_separates_languages(self, catalog):
        """Книги на разных языках образуют разные группы."""
        b_ru = _make_book("Title", lang="ru", author_names=["Author"], catalog=catalog)
        b_en = _make_book("Title", lang="en", author_names=["Author"], catalog=catalog)

        result = DuplicatesService.find_all_duplicates()

        # Каждая книга — единственная в своей "группе"
        assert b_ru.id not in result
        assert b_en.id not in result

    def test_empty_collection(self):
        """Пустая коллекция возвращает пустой результат."""
        result = DuplicatesService.find_all_duplicates()
        assert result == {}

    def test_excludes_self_from_group(self, catalog):
        """Книга не считается дублем самой себя."""
        b = _make_book("Дубликат", author_names=["Автор"], catalog=catalog)
        _make_book("Дубликат", author_names=["Автор"], catalog=catalog)

        result = DuplicatesService.find_all_duplicates()

        doubles_for_b = list(result.get(b.id, []))
        assert b not in doubles_for_b
