"""Тесты сортировки при пагинации."""

import pytest

from opds_catalog.models import Book, Series, bseries
from opds_catalog.services import book_services

pytestmark = pytest.mark.django_db


def _create_book(catalog, title, docdate=""):
    return Book.objects.create(
        filename=f"{title}.fb2",
        path=".",
        format="fb2",
        title=title,
        search_title=title.upper(),
        docdate=docdate,
        catalog=catalog,
    )


class TestPaginatedOrdering:
    def test_series_search_preserves_ser_no_ordering(self, catalog):
        """Книги серии должны идти по номеру в серии, а не по названию."""
        series = Series.objects.create(ser="Test Series", search_ser="TEST SERIES")

        # Номера серий намеренно не совпадают с алфавитным порядком названий
        books = {
            "A": _create_book(catalog, "A", "2020"),
            "C": _create_book(catalog, "C", "2021"),
            "B": _create_book(catalog, "B", "2022"),
        }
        bseries.objects.create(book=books["A"], ser=series, ser_no=3)
        bseries.objects.create(book=books["C"], ser=series, ser_no=1)
        bseries.objects.create(book=books["B"], ser=series, ser_no=2)

        queryset = book_services.search_book("s", str(series.id), None, None)
        items, _ = book_services.paginated_book_content(queryset, 1)

        titles = [item["title"] for item in items]
        # По ser_no: C (1), B (2), A (3). По алфавиту было бы A, B, C.
        assert titles == ["C", "B", "A"]

    def test_bookshelf_preserves_readtime_ordering(self, catalog, django_user):
        """Книжная полка должна сортироваться по времени чтения."""
        from opds_catalog.models import bookshelf

        b1 = _create_book(catalog, "AAA", "2020")
        b2 = _create_book(catalog, "BBB", "2021")
        bookshelf.objects.create(user=django_user, book=b1)
        bookshelf.objects.create(user=django_user, book=b2)

        queryset = book_services.search_book("u", "", None, django_user)
        items, _ = book_services.paginated_book_content(
            queryset, 1, user=django_user, auth_enabled=True
        )

        titles = [item["title"] for item in items]
        # По времени чтения: b2 (позже), затем b1
        assert titles[0] == "BBB"

    def test_plain_search_falls_back_to_default_ordering(self, catalog):
        """Обычный поиск сохраняет сортировку по умолчанию."""
        _create_book(catalog, "C", "2022")
        _create_book(catalog, "A", "2021")
        _create_book(catalog, "B", "2020")

        queryset = book_services.search_book("m", "", None, None)
        items, _ = book_services.paginated_book_content(queryset, 1)

        titles = [item["title"] for item in items]
        assert titles == ["A", "B", "C"]
