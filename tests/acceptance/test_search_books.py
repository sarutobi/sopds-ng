"""Тесты для SearchBooksView."""

import pytest
from django.urls import reverse

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

    def test_search_by_series(self, client, django_user, catalog, series):
        from opds_catalog.models import Counter

        Counter.obj.create(name="allbooks", value=0)
        client.force_login(django_user)
        book = Book.objects.create(
            filename="t1.fb2",
            path=".",
            format="fb2",
            search_title="Series Book",
            title="Series Book",
            catalog=catalog,
        )
        book.series.set([series])
        response = client.get(
            reverse("web:searchbooks"),
            {"searchtype": "s", "searchterms": str(series.id)},
        )
        assert response.status_code == 200

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

    def test_search_doubles(self, client, django_user, catalog):
        from opds_catalog.models import Author, Counter

        Counter.obj.create(name="allbooks", value=0)
        client.force_login(django_user)
        b1 = Book.objects.create(
            filename="t1.fb2",
            path=".",
            format="fb2",
            search_title="Double",
            title="Double",
            catalog=catalog,
        )
        b2 = Book.objects.create(
            filename="t2.fb2",
            path=".",
            format="fb2",
            search_title="Double",
            title="Double",
            catalog=catalog,
        )
        a = Author.objects.create(full_name="SAME", search_full_name="SAME")
        b1.authors.set([a])
        b2.authors.set([a])

        response = client.get(
            reverse("web:searchbooks"), {"searchtype": "d", "searchterms": str(b1.id)}
        )
        assert response.status_code == 200

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
