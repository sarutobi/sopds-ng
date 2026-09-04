"""Тесты отсутствия аутентификации для SearchSuggestView."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestSearchSuggestAuth:
    """Тест проверки доступа к SearchSuggestView без авторизации."""

    def test_suggest_unauthenticated(self, client, book) -> None:
        """Запрос к SearchSuggestView без авторизации должен возвращать 403 (или редирект на login)."""
        # Мы ожидаем, что сейчас тест упадет (вернет 200), так как декоратор закомментирован.
        response = client.post(
            reverse("web:suggest"), {"searchterms": book.title[:3], "type": "title"}
        )
        # Если декоратор @sopds_login работает, он либо вернет 403, либо редирект на login.
        # Судя по handler403 в views.py, он возвращает 403.
        assert response.status_code in [403, 302]
