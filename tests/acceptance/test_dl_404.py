"""Тесты обработки 404 для несуществующих книг в dl.py."""

import pytest
from django.urls import reverse

pytestmark = [pytest.mark.django_db]


@pytest.mark.parametrize(
    "url_name, args",
    [
        ("opds:download", (999999, 0)),
        ("opds:cover", (999999,)),
        ("opds:thumb", (999999,)),
        ("opds:convert", (999999, "epub")),
    ],
)
def test_nonexistent_book_returns_404(client, django_user, url_name, args):
    """Проверка, что запрос к несуществующему book_id возвращает 404."""
    client.force_login(django_user)
    url = reverse(url_name, args=args)
    response = client.get(url)
    assert response.status_code == 404
