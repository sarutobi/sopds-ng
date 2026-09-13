"""Тесты скачивания книг через HTTP — acceptance, с клиентом и БД."""

import base64
import os
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from constance import config
from django.urls import reverse

from opds_catalog.models import Book
from opds_catalog.utils import getFileDataConv

pytestmark = [pytest.mark.django_db, pytest.mark.acceptance]


# ── Downloads (скачивание книг через HTTP) ──────────────────────────────


@pytest.mark.usefixtures("fake_sopds_root_lib", "django_user", "load_db_data")
class TestDownloads:
    """Тесты endpoint'а скачивания книг."""

    @pytest.mark.override_config(SOPDS_AUTH=True)
    def test_unauthorized_downloads(self, client) -> None:
        response = client.get(reverse("opds:download", args=(5, 0)))
        assert response.status_code == 401

    @pytest.mark.override_config(SOPDS_AUTH=True)
    def test_authorized_download_book(self, client, django_user) -> None:
        client.force_login(django_user)
        response = client.get(reverse("opds:download", args=(5, 0)))
        assert response.status_code == 200
        assert response["Content-Length"] == "495374"

    @pytest.mark.override_config(SOPDS_AUTH=True)
    def test_basic_authentication(self, client, django_user, django_user_model) -> None:
        response = client.get(reverse("opds:download", args=(5, 0)))
        assert response.status_code == 401
        credentials = "test:secret"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        authorization_header = f"Basic {encoded_credentials}"
        response = client.get(
            reverse("opds:download", args=(5, 0)),
            HTTP_AUTHORIZATION=authorization_header,
        )
        assert response.status_code == 200
        assert response["Content-Length"] == "495374"

    @pytest.mark.override_config(SOPDS_AUTH=False)
    def test_download_zip(self, client) -> None:
        response = client.get(reverse("opds:download", args=(5, 1)))
        assert response.status_code == 200
        assert response["Content-Length"] == "219509"

    @pytest.mark.override_config(SOPDS_AUTH=False)
    def test_download_unexisted_book(self, client, unexisted_book) -> None:
        response = client.get(reverse("opds:download", args=(4, 0)))
        assert response.status_code == 404


# ── Обложки и thumbnail ──────────────────────────────────────────────────


@pytest.mark.parametrize("use_sax", [(True), (False)])
def test_get_book_cover(
    fake_sopds_root_lib, create_regular_book, client, override_config, use_sax
) -> None:
    """Обложка книги (FB2SAX вкл/выкл)."""
    book: Book = create_regular_book
    assert book is not None
    url = reverse("opds:cover", args=(book.id,))
    with override_config(SOPDS_FB2SAX=use_sax):
        actual = client.get(url)
        assert actual.status_code == 200
        assert actual["Content-Length"] == "56360"


def test_cover_redirect_when_no_cover(
    fake_sopds_root_lib,
    create_regular_book,
    client,
) -> None:
    """Cover без обложки -> редирект на заглушку."""
    book: Book = create_regular_book
    book.filename = "nonexist.fb2"
    book.save()
    url = reverse("opds:cover", args=(book.id,))
    response = client.get(url)
    assert response.status_code == 302
    assert "nocover" in response.url


def test_thumbnail(
    fake_sopds_root_lib, create_regular_book, client, override_config
) -> None:
    """Проверка Thumbnail."""
    book: Book = create_regular_book
    url = reverse("opds:thumb", args=(book.id,))
    with override_config(SOPDS_FB2SAX=True):
        response = client.get(url)
    assert response.status_code == 200
    assert response["Content-Type"] == "image/jpeg"


# ── Вспомогательные тесты загрузок ───────────────────────────────────────


def test_wrong_encoded_fb2_zip(test_rootlib) -> None:
    """Чтение файла из ZIP архива с кодировкой, отличной от latin1(cp437)."""
    from opds_catalog.utils import read_from_zipped_file

    actual = read_from_zipped_file(
        os.path.join(test_rootlib, "wrong_encoded.zip"),
        "Носов - Незнайка-путешественник.fb2",
    )
    assert actual is not None


class TestGetFileDataConv:
    """Тесты конвертации книг (unit/integration)."""

    def test_convert_non_fb2_book(self) -> None:
        book = Book(title="Not a fb2 book", format="pdf")
        actual = getFileDataConv(book, "epub")
        assert actual is None

    def test_convert_absent_book(self) -> None:
        book = Book(
            title="I'm not exists", filename="263001.fb2", cat_type="0", path="data"
        )
        actual = getFileDataConv(book, "epub")
        assert actual is None
