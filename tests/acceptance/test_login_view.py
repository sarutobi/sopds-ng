"""Тесты LoginView: валидация next_url, защита от open redirect."""

from django.urls import reverse
import pytest


@pytest.mark.django_db
class TestLoginViewRedirect:
    """Проверка редиректов LoginView при успешной аутентификации."""

    def test_login_redirect_success(self, client, django_user) -> None:
        """POST с валидным next -> редирект на этот URL."""
        response = client.post(
            reverse("web:login") + "?next=/web/authors",
            {"username": "test", "password": "secret"},
        )
        assert response.status_code == 302
        assert response["Location"] == "/web/authors"

    def test_login_redirect_fallback(self, client, django_user) -> None:
        """POST с next=http://evil.com -> редирект на web:main (защита от open redirect)."""
        response = client.post(
            reverse("web:login") + "?next=http://evil.com",
            {"username": "test", "password": "secret"},
        )
        assert response.status_code == 302
        assert response["Location"] == reverse("web:main")

    def test_login_redirect_empty_next(self, client, django_user) -> None:
        """POST без next -> редирект на web:main по умолчанию."""
        response = client.post(
            reverse("web:login"),
            {"username": "test", "password": "secret"},
        )
        assert response.status_code == 302
        assert response["Location"] == reverse("web:main")

    def test_login_redirect_relative(self, client, django_user) -> None:
        """POST с next=/web/books -> редирект на /web/books (относительный разрешён)."""
        response = client.post(
            reverse("web:login") + "?next=/web/books",
            {"username": "test", "password": "secret"},
        )
        assert response.status_code == 302
        assert response["Location"] == "/web/books"

    def test_login_redirect_protocol_relative(self, client, django_user) -> None:
        """POST с next=//evil.com -> редирект на web:main (protocol-relative URL bypass)."""
        response = client.post(
            reverse("web:login") + "?next=//evil.com",
            {"username": "test", "password": "secret"},
        )
        assert response.status_code == 302
        assert response["Location"] == reverse("web:main")

    def test_login_redirect_same_host_full_url(self, client, django_user) -> None:
        """POST с next=http://testserver/web/ -> редирект разрешён (свой хост)."""
        response = client.post(
            reverse("web:login") + "?next=http://testserver/web/",
            {"username": "test", "password": "secret"},
        )
        assert response.status_code == 302
        assert response["Location"] == "http://testserver/web/"
