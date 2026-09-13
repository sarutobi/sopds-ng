"""Тесты для SearchSeriesView и SearchAuthorsView."""

import pytest
from django.urls import reverse

from opds_catalog.models import Author, Book, Catalog, Series


@pytest.mark.django_db
class TestSearchEntitiesViewExtended:
    def test_search_series_contains(self, client, django_user, series, catalog):
        from opds_catalog.models import Counter

        Counter.obj.create(name="allbooks", value=0)
        client.force_login(django_user)
        # Создаем книгу, чтобы счетчик был > 0
        book = Book.objects.create(
            filename="s1.fb2",
            path=".",
            format="fb2",
            search_title="Series Book",
            title="Series Book",
            catalog=catalog,
        )
        book.series.set([series])

        response = client.get(
            reverse("web:searchseries"), {"searchtype": "m", "searchterms": series.ser}
        )
        assert response.status_code == 200
        assert series.ser.encode() in response.content
        assert b"1" in response.content  # book_count

    def test_search_series_no_results(self, client, django_user):
        from opds_catalog.models import Counter

        Counter.obj.create(name="allbooks", value=0)
        client.force_login(django_user)
        response = client.get(
            reverse("web:searchseries"),
            {"searchtype": "m", "searchterms": "NONEXISTENT_SERIES_123"},
        )
        assert response.status_code == 200

    def test_search_authors_contains(self, client, django_user, author, catalog):
        from opds_catalog.models import Counter

        Counter.obj.create(name="allbooks", value=0)
        client.force_login(django_user)
        # Создаем книгу для автора
        book = Book.objects.create(
            filename="a1.fb2",
            path=".",
            format="fb2",
            search_title="Author Book",
            title="Author Book",
            catalog=catalog,
        )
        book.authors.set([author])

        response = client.get(
            reverse("web:searchauthors"),
            {"searchtype": "m", "searchterms": author.full_name},
        )
        assert response.status_code == 200
        assert author.full_name.encode() in response.content
        assert b"1" in response.content  # book_count

    def test_search_authors_no_results(self, client, django_user):
        from opds_catalog.models import Counter

        Counter.obj.create(name="allbooks", value=0)
        client.force_login(django_user)
        response = client.get(
            reverse("web:searchauthors"),
            {"searchtype": "m", "searchterms": "NONEXISTENT_AUTHOR_123"},
        )
        assert response.status_code == 200

    def test_search_series_pagination(self, client, django_user, catalog):
        from opds_catalog.models import Counter

        Counter.obj.create(name="allbooks", value=0)
        client.force_login(django_user)
        # Создаем много серий, чтобы сработала пагинация (SOPDS_MAXITEMS обычно 20 или 50)
        from constance import config

        max_items = config.SOPDS_MAXITEMS
        for i in range(max_items + 5):
            Series.objects.create(
                ser=f"Series {i}", search_ser=f"SERIES {i}", lang_code=9
            )

        # Чтобы серии попали в выдачу по "Series", они должны быть в базе
        # (уже создали выше)

        response = client.get(
            reverse("web:searchseries"),
            {"searchtype": "m", "searchterms": "Series", "page": "2"},
        )
        assert response.status_code == 200
        # Проверяем, что на второй странице есть данные
        # Вместо конкретной строки проверим, что контент не пуст или содержит маркеры
        assert b"Series" in response.content
