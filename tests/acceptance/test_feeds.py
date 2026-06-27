from io import BytesIO

import pytest
from constance import config
from django.urls import reverse
from django.utils.translation import gettext as _
from lxml import etree

from opds_catalog import opdsdb, settings
from tests.helpers import (
    opds_acquisition_links,
    opds_acquisition_or_navigation_feed,
    opds_content_duplication,
    opds_dc_namespace,
    opds_image_bitmap,
    opds_image_rel,
    opds_link_profile_kind,
    opds_requirement_links,
    opds_root_link,
    opds_search_rel,
    opds_summary_is_plain_text,
)

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.override_config(SOPDS_AUTH=False),
]


@pytest.mark.usefixtures("load_db_data")
class TestFeeds:  # acceptance
    """Тесты OPDS фидов (HTTP клиент, XML структура, авторизация)."""

    def test_main_feed(self, client) -> None:
        response = client.get("/opds/")
        assert response.status_code == 200
        response = client.get(reverse("opds:main"))
        assert response.status_code == 200
        assert _("By catalogs") in response.content.decode()
        assert (
            _("Catalogs: %(catalogs)s, books: %(books)s.") % {"catalogs": 2, "books": 4}
        ) in response.content.decode()
        assert (
            _("Authors: %(authors)s.") % {"authors": 4}
        ) in response.content.decode()
        assert (_("Genres: %(genres)s.") % {"genres": 4}) in response.content.decode()
        assert settings.SUBTITLE in response.content.decode()

    def test_catalogs_feed(self, client) -> None:
        response = client.get("/opds/catalogs/")
        assert response.status_code == 200
        response = client.get(reverse("opds:catalogs"))
        assert response.status_code == 200
        assert "books.zip" in response.content.decode()
        assert "The Sanctuary Sparrow" in response.content.decode()

    def test_catalogs_feed_tree(self, client) -> None:
        response = client.get("/opds/catalogs/4/")
        assert response.status_code == 200
        response = client.get(reverse("opds:cat_tree", args=["4"]))
        assert response.status_code == 200
        assert "Драконьи Услуги" in response.content.decode()
        assert "Китайски сладкиш с късметче" in response.content.decode()
        assert "Любовь в жизни Обломова" in response.content.decode()

    def test_open_search(self, client) -> None:
        response = client.get("/opds/search/")
        assert response.status_code == 200
        assert "www.sopds.ru" in response.content.decode()

    def test_search_types(self, client) -> None:
        response = client.get("/opds/search/Драк/")
        assert response.status_code == 200
        response = client.get(
            reverse("opds:searchtypes", kwargs={"searchterms": "Драк"})
        )
        assert response.status_code == 200
        assert _("Search by titles") in response.content.decode()

    def test_search_books(self, client) -> None:
        response = client.get("/opds/search/books/m/Драк/")
        assert response.status_code == 200
        response = client.get(
            reverse(
                "opds:searchbooks", kwargs={"searchtype": "m", "searchterms": "рак"}
            )
        )
        assert response.status_code == 200
        assert "Драконьи Услуги" in response.content.decode()
        assert "Куприянов Денис" in response.content.decode()
        response = client.get(
            reverse(
                "opds:searchbooks", kwargs={"searchtype": "b", "searchterms": "Драк"}
            )
        )
        assert response.status_code == 200
        assert "Драконьи Услуги" in response.content.decode()
        assert "Куприянов Денис" in response.content.decode()
        response = client.get(
            reverse("opds:searchbooks", kwargs={"searchtype": "a", "searchterms": "8"})
        )
        assert response.status_code == 200
        assert "Драконьи Услуги" in response.content.decode()
        assert "Куприянов Денис" in response.content.decode()
        assert (
            _("All books by %(full_name)s") % {"full_name": "Куприянов Денис"}
        ) in response.content.decode()
        assert "prose_contemporary" in response.content.decode()
        assert "<category " in response.content.decode()

    def test_search_authors(self, client) -> None:
        response = client.get("/opds/search/authors/m/Логинов/")
        assert response.status_code == 200
        response = client.get(
            reverse(
                "opds:searchauthors", kwargs={"searchtype": "m", "searchterms": "гинов"}
            )
        )
        assert response.status_code == 200
        assert "Логинов Святослав" in response.content.decode()
        response = client.get(
            reverse(
                "opds:searchauthors", kwargs={"searchtype": "b", "searchterms": "Лог"}
            )
        )
        assert response.status_code == 200
        assert "Логинов Святослав" in response.content.decode()

    def test_search_genres(self) -> None:
        pass

    def test_lang_feed(self, client) -> None:
        response = client.get("/opds/books/")
        assert response.status_code == 200
        response = client.get(reverse("opds:lang_books"))
        assert response.status_code == 200
        assert _("Cyrillic") in response.content.decode()
        assert _("Latin") in response.content.decode()
        assert _("Digits") in response.content.decode()
        assert _("Other symbols") in response.content.decode()
        assert _("Show all") in response.content.decode()

    def test_books_feed(self, client) -> None:
        response = client.get("/opds/books/0/")
        assert response.status_code == 200
        if config.SOPDS_ALPHABET_MENU:
            response = client.get(reverse("opds:lang_books"))
            assert response.status_code == 200
            assert _("Cyrillic") in response.content.decode()
        response = client.get(reverse("opds:char_books", kwargs={"lang_code": 0}))
        assert "<title>T</title>" in response.content.decode()

    def test_authors_feed(self, client) -> None:
        response = client.get("/opds/authors/0/")
        assert response.status_code == 200
        if config.SOPDS_ALPHABET_MENU:
            response = client.get(reverse("opds:lang_authors"))
            assert response.status_code == 200
            assert _("Cyrillic") in response.content.decode()
        response = client.get(reverse("opds:char_authors", kwargs={"lang_code": 0}))
        assert "<title>P</title>" in response.content.decode()

    def test_genres_feed(self, client) -> None:
        response = client.get("/opds/genres/")
        assert response.status_code == 200
        response = client.get(reverse("opds:genres"))
        assert response.status_code == 200
        assert opdsdb.unknown_genre_en in response.content.decode()
        response = client.get(reverse("opds:genres", kwargs={"section": 232}))
        assert response.status_code == 200
        assert "prose_contemporary" in response.content.decode()


HTTP_OK = 200
HTTP_UNAUTHORIZED = 401


@pytest.mark.django_db
@pytest.mark.parametrize(
    "sopds_auth, expected", [(False, HTTP_OK), (True, HTTP_UNAUTHORIZED)]
)
def test_auth_feed(override_config, client, django_user, sopds_auth, expected) -> None:
    """Проверка работы авторизации для фидов."""
    with override_config(SOPDS_AUTH=sopds_auth):
        response = client.get("/opds/")
        assert response.status_code == expected

        client.force_login(django_user)
        response = client.get("/opds/")
        assert response.status_code == HTTP_OK


@pytest.mark.parametrize(
    "url",
    [
        reverse("opds_catalog:main"),
        reverse("opds_catalog:catalogs"),
        reverse("opds_catalog:lang_books"),
        reverse("opds_catalog:nolang_books"),
        reverse("opds_catalog:lang_authors"),
        reverse("opds_catalog:nolang_authors"),
        reverse("opds_catalog:lang_series"),
        reverse("opds_catalog:nolang_series"),
        reverse("opds_catalog:genres"),
    ],
)
@pytest.mark.django_db
def test_feed_structure(url, client, load_db_data, override_config, opds_1_2) -> None:
    """Проверка грамматичеcкой корректности фида и его валидация."""
    with override_config(SOPDS_AUTH=False):
        response = client.get(url)

    assert response is not None
    feed = etree.parse(BytesIO(response.content))
    assert _validate_opds_feed(feed, opds_1_2)
    assert opds_requirement_links(feed)
    assert opds_acquisition_links(feed)
    assert opds_search_rel(feed)
    assert opds_summary_is_plain_text(feed)
    assert opds_image_rel(feed)
    assert opds_image_bitmap(feed)
    assert opds_dc_namespace(feed)
    assert opds_content_duplication(feed)
    assert opds_root_link(feed)
    assert opds_link_profile_kind(feed)


def _validate_opds_feed(feed, schema) -> bool:
    validator = etree.RelaxNG(schema)
    result = validator.validate(feed)
    if not result:
        print(validator.error_log)
    return result
