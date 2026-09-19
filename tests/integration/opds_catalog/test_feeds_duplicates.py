"""Тесты OPDS-фидов в части отображения дубликатов."""

from __future__ import annotations

import pytest
from lxml import etree

from opds_catalog.feeds import BooksFeed
from opds_catalog.models import Author, Book, Catalog, bauthor
from opds_catalog.services.duplicates_service import DuplicatesService

pytestmark = pytest.mark.django_db


@pytest.fixture
def root_catalog(db):
    """Корневой каталог для тестов."""
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


class TestBooksFeedDuplicates:
    """Тесты формирования OPDS-фида для книг с дублями."""

    def test_doubles_link_uses_real_count(self, root_catalog):
        """Ссылка на дубликаты использует количество дублей из сервиса."""
        # Создаём книгу и её дубликат
        b1 = _make_book(
            "Война и мир",
            author_names=["Толстой"],
            catalog=root_catalog,
        )
        _make_book(
            "Война и мир",
            author_names=["Толстой"],
            catalog=root_catalog,
        )

        # Получаем дублей через сервис
        doubles = DuplicatesService.find_doubles_for_book(b1.id)
        assert doubles.count() == 1

    def test_no_duplicates_when_languages_differ(self, root_catalog):
        """Книги на разных языках не считаются дублями в OPDS-фиде."""
        b_ru = _make_book(
            "War and Peace",
            lang="ru",
            author_names=["Tolstoy"],
            catalog=root_catalog,
        )
        _make_book(
            "War and Peace",
            lang="en",
            author_names=["Tolstoy"],
            catalog=root_catalog,
        )

        doubles = DuplicatesService.find_doubles_for_book(b_ru.id)
        assert doubles.count() == 0
