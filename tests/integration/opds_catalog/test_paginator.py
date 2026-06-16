"""Тесты пагинации: paginated_book_content, paginated_catalog_content.

Покрывает поведение функций пагинации после замены кастомного PaginatorAdapter
на django.core.paginator.Paginator (задача 1.6).
"""

from __future__ import annotations

import pytest

from django.core.paginator import Paginator

from opds_catalog.models import Author, Book, Catalog, bauthor
from opds_catalog.services import book_services, catalog_services

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Django Paginator — unit-тесты
# ---------------------------------------------------------------------------


class TestDjangoPaginator:
    """Тесты django.core.paginator.Paginator (замена PaginatorAdapter)."""

    def test_simple_pagination(self):
        """10 элементов, MAXITEMS=6, страница 1 из 2."""
        paginator = Paginator(range(10), 6)
        page = paginator.page(1)
        assert len(page.object_list) == 6
        assert page.has_next() is True
        assert page.has_previous() is False
        assert page.number == 1
        assert paginator.num_pages == 2

    def test_last_page(self):
        """10 элементов, MAXITEMS=6, последняя страница."""
        paginator = Paginator(range(10), 6)
        page = paginator.page(2)
        assert len(page.object_list) == 4
        assert page.has_next() is False

    def test_single_page(self):
        """3 элемента, MAXITEMS=10 — одна страница."""
        paginator = Paginator(range(3), 10)
        page = paginator.page(1)
        assert paginator.num_pages == 1
        assert page.has_next() is False
        assert page.has_previous() is False

    def test_page_range(self):
        """50 элементов, MAXITEMS=5 — 10 страниц, range 1..10."""
        paginator = Paginator(range(50), 5)
        assert paginator.num_pages == 10
        assert list(paginator.page_range) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    def test_page_out_of_range(self):
        """Страница 99 для 3 элементов — EmptyPage."""
        paginator = Paginator(range(3), 4)
        from django.core.paginator import EmptyPage

        with pytest.raises(EmptyPage):
            paginator.page(99)


# ---------------------------------------------------------------------------
# paginated_book_content — тесты
# ---------------------------------------------------------------------------


class TestPaginatedBookContent:
    """Тесты book_services.paginated_book_content()."""

    def test_single_page(self, book_with_relations):
        """Одна книга — одна страница."""
        books = Book.objects.all()
        items, paginator = book_services.paginated_book_content(
            Book.objects.order_by("id"), 1, True
        )
        assert len(items) == 1
        assert paginator["number"] == 1
        assert paginator["has_next"] is False

    @pytest.mark.override_config(SOPDS_MAXITEMS=4, SOPDS_DOUBLES_HIDE=True)
    def test_multiple_pages_page1(self, catalog):
        """10 книг с разными названиями, MAXITEMS=4, страница 1 — 4 книги."""
        _create_unique_books(catalog, 10)
        books = Book.objects.order_by("search_title")
        items, paginator = book_services.paginated_book_content(books, 1, False)
        assert len(items) == 4
        assert paginator["number"] == 1
        assert paginator["has_next"] is True
        assert paginator["num_pages"] == 3

    @pytest.mark.override_config(SOPDS_MAXITEMS=4, SOPDS_DOUBLES_HIDE=True)
    def test_multiple_pages_page2(self, catalog):
        """10 книг с разными названиями, MAXITEMS=4, страница 2 — 4 книги."""
        _create_unique_books(catalog, 10)
        books = Book.objects.order_by("search_title")
        items, paginator = book_services.paginated_book_content(books, 2, False)
        assert len(items) == 4
        assert paginator["number"] == 2

    @pytest.mark.override_config(SOPDS_MAXITEMS=4, SOPDS_DOUBLES_HIDE=True)
    def test_multiple_pages_page3(self, catalog):
        """10 книг с разными названиями, MAXITEMS=4, страница 3 — 2 книги."""
        _create_unique_books(catalog, 10)
        books = Book.objects.order_by("search_title")
        items, paginator = book_services.paginated_book_content(books, 3, False)
        assert len(items) == 2
        assert paginator["number"] == 3
        assert paginator["has_next"] is False

    @pytest.mark.override_config(SOPDS_MAXITEMS=4, SOPDS_DOUBLES_HIDE=True)
    def test_doubles_across_page_boundary(self, catalog):
        """3 дубликата среди 10 книг, MAXITEMS=4 — дубликаты дотягиваются."""
        author = _create_author()
        _create_books_for_author(catalog, author, 3, "Дубликат")
        _create_books_for_author(catalog, author, 7, "Обычная")
        books = Book.objects.order_by("search_title")
        items, paginator = book_services.paginated_book_content(books, 1, False)
        assert paginator["number"] == 1
        assert items[0]["title"] == "Дубликат"
        assert items[0]["doubles"] == 2  # 3 одинаковых = 1 основной + 2 дубля

    @pytest.mark.override_config(SOPDS_MAXITEMS=4, SOPDS_DOUBLES_HIDE=False)
    def test_doubles_disabled(self, catalog):
        """SOPDS_DOUBLES_HIDE=False — дубликаты не скрываются."""
        author = _create_author()
        _create_books_for_author(catalog, author, 3, "Одинаковые")
        _create_books_for_author(catalog, author, 3, "Разные")
        books = Book.objects.order_by("search_title")
        items, _ = book_services.paginated_book_content(books, 1, False)
        assert len(items) == 4  # MAXITEMS=4
        assert all(item["doubles"] == 0 for item in items)


# ---------------------------------------------------------------------------
# paginated_catalog_content — тесты
# ---------------------------------------------------------------------------


class TestPaginatedCatalogContent:
    """Тесты catalog_services.paginated_catalog_content()."""

    def test_empty_catalog(self, catalog):
        """Пустой каталог — пустой результат."""
        items, pager_data = catalog_services.paginated_catalog_content(catalog, 1, 10)
        assert items == []
        assert pager_data["number"] == 1
        assert pager_data["has_next"] is False

    def test_only_catalogs(self, catalog):
        """Только подкаталоги, без книг."""
        for i in range(3):
            Catalog.objects.create(
                parent=catalog, cat_name=f"Подкат{i}", path=f"./{i}", cat_type=0
            )
        items, pager_data = catalog_services.paginated_catalog_content(catalog, 1, 10)
        assert len(items) == 3
        assert all(item["is_catalog"] == 1 for item in items)

    def test_only_books(self, catalog):
        """Только книги, без подкаталогов."""
        _create_unique_books(catalog, 5)
        items, pager_data = catalog_services.paginated_catalog_content(catalog, 1, 10)
        assert len(items) == 5
        assert all(item["is_catalog"] == 0 for item in items)

    @pytest.mark.override_config(SOPDS_MAXITEMS=4)
    def test_mixed_catalog_first_page(self, catalog):
        """3 подкаталога + 5 книг, MAXITEMS=4, страница 1 — 3 ката + 1 книга."""
        for i in range(3):
            Catalog.objects.create(
                parent=catalog, cat_name=f"Подкат{i}", path=f"./{i}", cat_type=0
            )
        _create_unique_books(catalog, 5)

        items, pager_data = catalog_services.paginated_catalog_content(catalog, 1, 4)
        # Единый список с Django Paginator: первые 4 из 8 элементов
        catalogs = [i for i in items if i["is_catalog"]]
        books = [i for i in items if not i["is_catalog"]]
        assert len(catalogs) == 3
        assert len(books) == 1
        assert pager_data["has_next"] is True
        assert pager_data["num_pages"] == 2

    @pytest.mark.override_config(SOPDS_MAXITEMS=4)
    def test_mixed_catalog_last_page(self, catalog):
        """3 подкаталога + 5 книг, MAXITEMS=4, страница 2 — 4 книги."""
        for i in range(3):
            Catalog.objects.create(
                parent=catalog, cat_name=f"Подкат{i}", path=f"./{i}", cat_type=0
            )
        _create_unique_books(catalog, 5)

        items, pager_data = catalog_services.paginated_catalog_content(catalog, 2, 4)
        # Единый список с Django Paginator: элементы 4-7 → 4 книги
        catalogs = [i for i in items if i["is_catalog"]]
        books = [i for i in items if not i["is_catalog"]]
        assert len(catalogs) == 0
        assert len(books) == 4
        assert pager_data["has_next"] is False

    @pytest.mark.override_config(SOPDS_MAXITEMS=4)
    def test_mixed_catalog_page_out_of_range(self, catalog):
        """Страница за пределами — возвращается последняя страница."""
        for i in range(3):
            Catalog.objects.create(
                parent=catalog, cat_name=f"Подкат{i}", path=f"./{i}", cat_type=0
            )
        items, pager_data = catalog_services.paginated_catalog_content(catalog, 99, 4)
        # EmptyPage → последняя страница (страница 1, т.к. всего 3 элемента)
        assert len(items) == 3


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------


def _create_author() -> Author:
    """Создаёт тестового автора."""
    author, _ = Author.objects.get_or_create(
        full_name="Тестовый Автор",
        defaults={"search_full_name": "ТЕСТОВЫЙ АВТОР"},
    )
    return author


def _create_unique_books(catalog: Catalog, count: int) -> list[Book]:
    """Создаёт count книг с уникальными названиями."""
    author = _create_author()
    books: list[Book] = []
    for i in range(count):
        title = f"Книга {i:04d}"
        book = Book.objects.create(
            filename=f"book_{i}.fb2",
            path=".",
            format="fb2",
            cat_type=0,
            title=title,
            search_title=title.upper(),
            catalog=catalog,
        )
        bauthor.objects.create(book=book, author=author)
        books.append(book)
    return books


def _create_books_for_author(
    catalog: Catalog, author: Author, count: int, title: str
) -> list[Book]:
    """Создаёт count книг с одинаковым названием и автором."""
    books: list[Book] = []
    for i in range(count):
        book = Book.objects.create(
            filename=f"book_{title}_{i}.fb2",
            path=".",
            format="fb2",
            cat_type=0,
            title=title,
            search_title=title.upper(),
            catalog=catalog,
        )
        bauthor.objects.create(book=book, author=author)
        books.append(book)
    return books
