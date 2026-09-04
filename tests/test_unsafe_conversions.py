import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
class TestUnsafeConversions:
    def test_search_books_doubles_invalid_id(self, client):
        # Line 150: book_id = int(args["searchterms"])
        client.force_login(None)  # We need a user to avoid 302 to login
        # If no user is provided, we can create one
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="testuser", password="password")
        client.force_login(user)

        response = client.get(
            reverse("opds_web_backend:searchbooks"),
            {"searchtype": "d", "searchterms": "abc"},
        )
        assert response.status_code == 500

    def test_search_series_invalid_page(self, client):
        # Line 210: page_num = int(request.GET.get("page", "1"))
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="testuser2", password="password")
        client.force_login(user)

        response = client.get(reverse("opds_web_backend:searchseries"), {"page": "abc"})
        assert response.status_code == 500

    def test_search_authors_invalid_page(self, client):
        # Line 267: page_num = int(request.GET.get("page", "1"))
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="testuser3", password="password")
        client.force_login(user)

        response = client.get(
            reverse("opds_web_backend:searchauthors"), {"page": "abc"}
        )
        assert response.status_code == 500

    def test_catalogs_invalid_page(self, client):
        # Line 331: page_num = int(request.GET.get("page", "1"))
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="testuser4", password="password")
        client.force_login(user)

        response = client.get(reverse("opds_web_backend:catalog"), {"page": "abc"})
        assert response.status_code == 500

    def test_series_invalid_lang(self, client):
        # Line 430: lang_code = int(request.GET.get("lang", "0"))
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="testuser5", password="password")
        client.force_login(user)

        response = client.get(reverse("opds_web_backend:series"), {"lang": "abc"})
        assert response.status_code == 500

    def test_bs_del_invalid_book(self, client):
        # Line 524: book = int(book)
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="testuser6", password="password")
        client.force_login(user)

        response = client.get(reverse("opds_web_backend:bsdel"), {"book": "abc"})
        assert response.status_code == 500
