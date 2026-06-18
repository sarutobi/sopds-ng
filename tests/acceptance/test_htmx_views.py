"""Тесты для htmx-ориентированных views (Задача 1.10)."""

from django.urls import reverse

import pytest


@pytest.mark.django_db
class TestSearchSuggestView:
    """Тесты для SearchSuggestView (автодополнение поиска)."""

    def test_suggest_short_query(self, client, django_user, update_counters) -> None:
        """Короткий запрос (< 2 символов) возвращает пустой ответ."""
        client.force_login(django_user)
        response = client.get(reverse("web:suggest"), {"q": "a", "type": "title"})
        assert response.status_code == 200
        assert response.content == b""

    def test_suggest_no_query(self, client, django_user, update_counters) -> None:
        """Пустой запрос возвращает пустой ответ."""
        client.force_login(django_user)
        response = client.get(reverse("web:suggest"), {"q": "", "type": "title"})
        assert response.status_code == 200
        assert response.content == b""

    def test_suggest_no_results(self, client, django_user, update_counters) -> None:
        """Запрос без совпадений возвращает HTML с 'No results'."""
        client.force_login(django_user)
        response = client.get(
            reverse("web:suggest"), {"q": "ZZZZZXXXXX", "type": "title"}
        )
        assert response.status_code == 200
        assert b"No results" in response.content

    def test_suggest_title_match(
        self, client, django_user, update_counters, book
    ) -> None:
        """Поиск по title находит книгу."""
        client.force_login(django_user)
        response = client.get(
            reverse("web:suggest"), {"q": book.title[:3], "type": "title"}
        )
        assert response.status_code == 200
        assert response.content != b""
        assert b"sopds-suggestion-item" in response.content

    def test_suggest_author_match(
        self, client, django_user, update_counters, author
    ) -> None:
        """Поиск по author находит автора."""
        client.force_login(django_user)
        response = client.get(
            reverse("web:suggest"),
            {"q": author.full_name[:3], "type": "author"},
        )
        assert response.status_code == 200
        assert b"sopds-suggestion-item" in response.content

    def test_suggest_invalid_type(self, client, django_user, update_counters) -> None:
        """Неизвестный search_type возвращает пустой результат."""
        client.force_login(django_user)
        response = client.get(reverse("web:suggest"), {"q": "test", "type": "invalid"})
        assert response.status_code == 200
        assert b"No results" in response.content or response.content == b""


@pytest.mark.django_db
class TestBSDelViewHtmx:
    """Тесты BSDelView с htmx-заголовками."""

    def test_delete_with_hx_request(
        self, client, django_user, update_counters, book_with_relations
    ) -> None:
        """DELETE-запрос с HX-Request возвращает HX-Redirect."""
        from opds_catalog.models import bookshelf

        bookshelf.objects.create(user=django_user, book=book_with_relations)
        client.force_login(django_user)

        url = f"{reverse('web:bsdel')}?book={book_with_relations.id}"
        response = client.delete(url, HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        assert "HX-Redirect" in response.headers

    def test_delete_without_hx(
        self, client, django_user, update_counters, book_with_relations
    ) -> None:
        """Обычный GET-запрос возвращает 302 (редирект)."""
        from opds_catalog.models import bookshelf

        bookshelf.objects.create(user=django_user, book=book_with_relations)
        client.force_login(django_user)

        response = client.get(
            reverse("web:bsdel"),
            {"book": str(book_with_relations.id)},
        )
        assert response.status_code == 302

    def test_delete_method_not_allowed(
        self, client, django_user, update_counters, book_with_relations
    ) -> None:
        """POST-запрос возвращает 405."""
        from opds_catalog.models import bookshelf

        bookshelf.objects.create(user=django_user, book=book_with_relations)
        client.force_login(django_user)

        response = client.post(
            reverse("web:bsdel"),
            {"book": str(book_with_relations.id)},
        )
        assert response.status_code == 405


@pytest.mark.django_db
class TestHtmxPagination:
    """Тесты htmx-пагинации — страницы возвращаются с htmx-заголовком."""

    def test_books_page_with_hx(self, client, django_user, update_counters) -> None:
        """Запрос страницы книг с HX-Request."""
        client.force_login(django_user)
        response = client.get(
            reverse("web:searchbooks"),
            {"searchtype": "m", "searchterms": "", "page": "1"},
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200

    def test_authors_page_with_hx(self, client, django_user, update_counters) -> None:
        """Запрос страницы авторов с HX-Request."""
        client.force_login(django_user)
        response = client.get(
            reverse("web:searchauthors"),
            {"searchtype": "m", "searchterms": "", "page": "1"},
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200

    def test_series_page_with_hx(self, client, django_user, update_counters) -> None:
        """Запрос страницы серий с HX-Request."""
        client.force_login(django_user)
        response = client.get(
            reverse("web:searchseries"),
            {"searchtype": "m", "searchterms": "", "page": "1"},
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
