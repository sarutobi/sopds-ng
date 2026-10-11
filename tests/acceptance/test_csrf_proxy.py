"""Тесты CSRF за reverse proxy (TLS терминируется на прокси).

Проверяет поведение логина, когда приложение получает http с заголовком
X-Forwarded-Proto: https от reverse proxy.
"""

import pytest
from django.test import Client, override_settings
from django.urls import reverse

LOGIN_DATA = {"username": "test", "password": "secret"}


def _get_csrf_token(client: Client, **kwargs) -> str:
    """Получение CSRF-токена со страницы логина."""
    response = client.get(reverse("web:login"), **kwargs)
    assert response.status_code == 200
    return client.cookies["csrftoken"].value


@pytest.fixture()
def strict_client() -> Client:
    """Клиент с принудительной проверкой CSRF (в тестах по умолчанию отключена)."""
    return Client(enforce_csrf_checks=True)


def _post_login(client: Client, token: str, **kwargs):
    """POST формы логина с CSRF-токеном и переданными заголовками."""
    data = {**LOGIN_DATA, "csrfmiddlewaretoken": token}
    return client.post(reverse("web:login"), data, **kwargs)


@pytest.mark.django_db
class TestCsrfBehindProxy:
    def test_login_behind_proxy_with_trusted_header(self, strict_client, django_user):
        """Прокси прислал X-Forwarded-Proto: https -> логин проходит (302, а не 403)."""
        with override_settings(
            ALLOWED_HOSTS=["testserver", "example.com"],
            SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
            CSRF_TRUSTED_ORIGINS=["https://example.com"],
        ):
            token = _get_csrf_token(
                strict_client,
                secure=True,
                HTTP_X_FORWARDED_PROTO="https",
                HTTP_HOST="example.com",
            )
            response = _post_login(
                strict_client,
                token,
                secure=True,
                HTTP_X_FORWARDED_PROTO="https",
                HTTP_HOST="example.com",
                HTTP_ORIGIN="https://example.com",
            )
        assert response.status_code == 302

    def test_login_same_origin_without_trusted_list(self, strict_client, django_user):
        """Same-origin проверка проходит без CSRF_TRUSTED_ORIGINS, если домен в ALLOWED_HOSTS."""
        with override_settings(
            SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
            CSRF_TRUSTED_ORIGINS=[],
            ALLOWED_HOSTS=["testserver", "example.com"],
        ):
            token = _get_csrf_token(
                strict_client,
                secure=True,
                HTTP_X_FORWARDED_PROTO="https",
                HTTP_HOST="example.com",
            )
            response = _post_login(
                strict_client,
                token,
                secure=True,
                HTTP_X_FORWARDED_PROTO="https",
                HTTP_HOST="example.com",
                HTTP_ORIGIN="https://example.com",
            )
        assert response.status_code == 302

    def test_login_403_when_proxy_header_not_trusted(self, strict_client, django_user):
        """Без SECURE_PROXY_SSL_HEADER запрос https-прокси отклоняется (403).

        Текущее поведение в проде: Origin https://<домен> сравнивается с
        http-схемой запроса и не проходит проверку.
        """
        with override_settings(
            ALLOWED_HOSTS=["testserver", "example.com"],
            SECURE_PROXY_SSL_HEADER=None,
        ):
            token = _get_csrf_token(strict_client)
            response = _post_login(
                strict_client,
                token,
                HTTP_HOST="example.com",
                HTTP_ORIGIN="https://example.com",
            )
        assert response.status_code == 403

    def test_login_403_when_https_disabled(self, strict_client, django_user):
        """SOPDS_USE_HTTPS=False: доверия заголовку нет, запрос за прокси отклоняется."""
        with override_settings(
            ALLOWED_HOSTS=["testserver", "example.com"],
            SECURE_PROXY_SSL_HEADER=None,
            CSRF_TRUSTED_ORIGINS=[],
        ):
            token = _get_csrf_token(strict_client)
            response = _post_login(
                strict_client,
                token,
                HTTP_HOST="example.com",
                HTTP_ORIGIN="https://example.com",
            )
        assert response.status_code == 403
