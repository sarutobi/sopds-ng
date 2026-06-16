"""Тесты middleware SOPDS.

Проверяет:
- SOPDSLocaleMiddleware: установка локали из настроек
- FetchFromCacheMiddleware: кэширование для аутентифицированных пользователей
"""

import pytest
from django.http import HttpRequest


pytestmark = pytest.mark.django_db


class TestSOPDSLocaleMiddleware:
    """Тесты SOPDSLocaleMiddleware."""

    def test_locale_set_on_request(self) -> None:
        """Проверяет, что middleware устанавливает LANG и LANGUAGE_CODE."""
        from constance import config

        from opds_catalog.middleware import SOPDSLocaleMiddleware

        request = HttpRequest()
        middleware = SOPDSLocaleMiddleware(lambda r: None)
        middleware.process_request(request)

        assert request.LANG == config.SOPDS_LANGUAGE
        assert request.LANGUAGE_CODE == config.SOPDS_LANGUAGE

    def test_locale_activates_translation(self) -> None:
        """Проверяет, что middleware активирует перевод."""
        from django.utils import translation

        from opds_catalog.middleware import SOPDSLocaleMiddleware

        request = HttpRequest()
        middleware = SOPDSLocaleMiddleware(lambda r: None)
        middleware.process_request(request)

        assert translation.get_language() is not None


class TestFetchFromCacheMiddleware:
    """Тесты FetchFromCacheMiddleware."""

    def test_returns_none_for_unauthenticated(self) -> None:
        """Для неаутентифицированного пользователя возвращает None."""
        from opds_catalog.middleware import FetchFromCacheMiddleware

        request = HttpRequest()
        request.user = type("User", (), {"is_authenticated": False})()

        middleware = FetchFromCacheMiddleware(lambda r: None)
        result = middleware.process_request(request)

        assert result is None

    def test_calls_super_for_authenticated(self) -> None:
        """Для аутентифицированного пользователя вызывает родительский метод."""
        from opds_catalog.middleware import FetchFromCacheMiddleware

        request = HttpRequest()
        request.user = type("User", (), {"is_authenticated": True})()

        middleware = FetchFromCacheMiddleware(lambda r: None)
        result = middleware.process_request(request)

        # super().process_request вернёт None для запроса без кэша
        assert result is None
