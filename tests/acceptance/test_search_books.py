"""Тесты для SearchBooksView."""

from unittest.mock import PropertyMock, patch

import pytest
from django.urls import reverse

from opds_catalog.config import catalog_config
from opds_catalog.models import Author, Book, Catalog, Genre, Series, bookshelf


@pytest.mark.django_db
class TestSearchBooksViewExtended:
    def test_search_by_title(self, client, django_user, catalog):
        from opds_catalog.models import Counter

        Counter.obj.create(name="allbooks", value=0)
        client.force_login(django_user)
        Book.objects.create(
            filename="t1.fb2",
            path=".",
            format="fb2",
            search_title="TEST BOOK",
            title="TEST BOOK",
            catalog=catalog,
        )
        response = client.get(
            reverse("web:searchbooks"), {"searchtype": "m", "searchterms": "TEST"}
        )
        assert response.status_code == 200
        assert b"TEST BOOK" in response.content

    def test_search_by_author(self, client, django_user, catalog, author):
        from opds_catalog.models import Counter

        Counter.obj.create(name="allbooks", value=0)
        client.force_login(django_user)
        book = Book.objects.create(
            filename="t1.fb2",
            path=".",
            format="fb2",
            search_title="Author Book",
            title="Author Book",
            catalog=catalog,
        )
        book.authors.set([author])
        response = client.get(
            reverse("web:searchbooks"),
            {"searchtype": "a", "searchterms": str(author.id)},
        )
        assert response.status_code == 200

    def test_search_by_author_and_series(
        self, client, django_user, catalog, author, series
    ):
        from opds_catalog.models import Counter

        Counter.obj.create(name="allbooks", value=0)
        client.force_login(django_user)
        book = Book.objects.create(
            filename="t1.fb2",
            path=".",
            format="fb2",
            search_title="Author Series Book",
            title="Author Series Book",
            catalog=catalog,
        )
        book.authors.set([author])
        book.series.set([series])

        # searchtype 'as' for author and series
        response = client.get(
            reverse("web:searchbooks"),
            {
                "searchtype": "as",
                "searchterms": f"{author.id}",
                "searchterms0": f"{series.id}",
            },
        )
        assert response.status_code == 200
        assert b"Author Series Book" in response.content

    def test_search_by_genre(self, client, django_user, catalog):
        from opds_catalog.models import Counter, Genre

        Counter.obj.create(name="allbooks", value=0)
        client.force_login(django_user)
        genre = Genre.objects.create(genre="Genre", section="Sec", subsection="Sub")
        book = Book.objects.create(
            filename="t1.fb2",
            path=".",
            format="fb2",
            search_title="Genre Book",
            title="Genre Book",
            catalog=catalog,
        )
        book.genres.set([genre])
        response = client.get(
            reverse("web:searchbooks"),
            {"searchtype": "g", "searchterms": str(genre.id)},
        )
        assert response.status_code == 200

    def test_search_bookshelf(self, client, django_user, catalog):
        from opds_catalog.models import Counter

        Counter.obj.create(name="allbooks", value=0)
        client.force_login(django_user)
        book = Book.objects.create(
            filename="t1.fb2",
            path=".",
            format="fb2",
            search_title="My Book",
            title="My Book",
            catalog=catalog,
        )
        bookshelf.objects.create(user=django_user, book=book)

        response = client.get(reverse("web:searchbooks"), {"searchtype": "u"})
        assert response.status_code == 200
        assert b"My Book" in response.content

    def test_search_doubles_hiding(self, client, django_user, catalog):
        """Проверка, что дубликаты скрываются в обычном поиске при включенной опции."""
        from opds_catalog.models import Author, Counter

        Counter.obj.create(name="allbooks", value=0)
        client.force_login(django_user)

        # Создаем одного автора
        author = Author.objects.create(
            full_name="Same Author", search_full_name="SAME AUTHOR"
        )

        # Создаем две идентичные книги
        Book.objects.create(
            filename="t1.fb2",
            path=".",
            format="fb2",
            search_title="Duplicate Book",
            title="Duplicate Book",
            catalog=catalog,
        )
        Book.objects.create(
            filename="t2.fb2",
            path=".",
            format="fb2",
            search_title="Duplicate Book",
            title="Duplicate Book",
            catalog=catalog,
        )

        # Привязываем автора к обеим книгам
        books = Book.objects.filter(title="Duplicate Book")
        for b in books:
            b.authors.set([author])

        # Чтобы гарантированно включить скрытие дублей, пропатчим свойства в классе SopdsConfig.
        # Так как это @property, мы заменяем его в словаре класса.
        from opds_catalog.config import SopdsConfig

        original_hide = SopdsConfig.DOUBLES_HIDE
        SopdsConfig.DOUBLES_HIDE = property(lambda self: True)
        try:
            response = client.get(
                reverse("web:searchbooks"),
                {"searchtype": "m", "searchterms": "Duplicate"},
            )
            assert response.status_code == 200
            content = response.content.decode()

            # Проверяем количество карточек книг.
            # При включенном скрытии дублей должна быть только одна карточка.
            assert content.count('class="cell sopds-book-card"') == 1
        finally:
            SopdsConfig.DOUBLES_HIDE = original_hide

    def test_search_by_id(self, client, django_user, catalog):
        from opds_catalog.models import Counter

        Counter.obj.create(name="allbooks", value=0)
        client.force_login(django_user)
        book = Book.objects.create(
            filename="t1.fb2",
            path=".",
            format="fb2",
            search_title="Id Book",
            title="Id Book",
            catalog=catalog,
        )
        response = client.get(
            reverse("web:searchbooks"), {"searchtype": "i", "searchterms": str(book.id)}
        )
        assert response.status_code == 200
        assert b"Id Book" in response.content

    @pytest.mark.parametrize(
        "params",
        [
            {"searchtype": "m", "searchterms": "test"},
            {"searchtype": "a", "searchterms": "1"},
            {"searchtype": "s", "searchterms": "1"},
            {"searchtype": "g", "searchterms": "1"},
            {"searchtype": "i", "searchterms": "1"},
            {"searchtype": "u", "searchterms": ""},
            {"searchtype": "d", "searchterms": "1"},
        ],
    )
    def test_search_pos_parametrized(self, client, django_user, catalog, params):
        from opds_catalog.models import Counter

        Counter.obj.create(name="allbooks", value=0)
        client.force_login(django_user)
        # Create minimum data to avoid 500s in services if needed, though 200 is the goal
        Book.objects.create(
            filename="t.fb2",
            path=".",
            format="fb2",
            search_title="TEST",
            title="TEST",
            catalog=catalog,
        )
        response = client.get(reverse("web:searchbooks"), params)
        assert response.status_code == 200

    def test_search_invalid_searchtype(self, client, django_user):
        client.force_login(django_user)
        response = client.get(
            reverse("web:searchbooks"), {"searchtype": "invalid", "searchterms": "test"}
        )
        assert response.status_code == 200  # Should be handled by ValueError block

    def test_search_invalid_page(self, client, django_user):
        client.force_login(django_user)
        # Negative page
        response = client.get(
            reverse("web:searchbooks"),
            {"searchtype": "m", "searchterms": "test", "page": "-5"},
        )
        assert response.status_code == 200
        # Non-numeric page
        response = client.get(
            reverse("web:searchbooks"),
            {"searchtype": "m", "searchterms": "test", "page": "abc"},
        )
        assert response.status_code == 200

    def test_search_auth_disabled(self, client, catalog):
        with patch(
            "opds_catalog.config.SopdsConfig.AUTH_ENABLED", new_callable=PropertyMock
        ) as mock_auth:
            mock_auth.return_value = False
            response = client.get(
                reverse("web:searchbooks"), {"searchtype": "m", "searchterms": "test"}
            )
            assert response.status_code == 200

    def test_search_auth_enabled_no_user(self, client):
        with patch(
            "opds_catalog.config.SopdsConfig.AUTH_ENABLED", new_callable=PropertyMock
        ) as mock_auth:
            mock_auth.return_value = True
            response = client.get(
                reverse("web:searchbooks"),
                {"searchtype": "m", "searchterms": "test"},
                follow_redirects=False,
            )
            assert response.status_code == 302

    def test_search_cache_t_logic(self, client, django_user, catalog):
        from opds_catalog.models import Counter

        Counter.obj.create(name="allbooks", value=0)
        client.force_login(django_user)

        # Case 1: Bookshelf (searchtype='u') -> cache_t = 0
        Book.objects.create(
            filename="u.fb2",
            path=".",
            format="fb2",
            search_title="U",
            title="U",
            catalog=catalog,
        )
        book = Book.objects.latest("id")
        bookshelf.objects.create(user=django_user, book=book)

        response = client.get(reverse("web:searchbooks"), {"searchtype": "u"})
        assert response.status_code == 200

        # Case 2: Regular search -> cache_t = catalog_config.CACHE_TIME
        response = client.get(
            reverse("web:searchbooks"), {"searchtype": "m", "searchterms": "U"}
        )
        assert response.status_code == 200
