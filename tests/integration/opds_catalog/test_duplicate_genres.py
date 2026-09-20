"""Регрессионные тесты БАГ-33: дублирование жанров не роняет сканер."""

import os

import pytest

from opds_catalog.db_utils import clear_all
from opds_catalog.models import Book
from opds_catalog.sopdscan import opdsScanner


def _fb2_with_duplicate_genres() -> bytes:
    """Валидный FB2 с дублирующимся и уникальным жанром (Detective, Detective, Sci-Fi)."""
    return (
        b'<?xml version="1.0" encoding="utf-8"?>\n'
        b'<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">'
        b"  <description>"
        b"    <title-info>"
        b"      <genre>Detective</genre>"
        b"      <genre>Detective</genre>"
        b"      <genre>Sci-Fi</genre>"
        b"      <author><first-name>Test</first-name><last-name>Author</last-name></author>"
        b"      <book-title>Test Book with Duplicate Genres</book-title>"
        b"      <lang>ru</lang>"
        b"    </title-info>"
        b"  </description>"
        b"  <body><section><title><p>Chapter</p></title><p>Test body text.</p></section></body>"
        b"</FictionBook>"
    )


@pytest.mark.django_db
def test_duplicate_genres_fb2(tmp_path) -> None:
    """Дубли жанров в FB2 не вызывают IntegrityError, сохраняются только уникальные."""
    clear_all()
    fb2_path = tmp_path / "duplicate_genres.fb2"
    fb2_path.write_bytes(_fb2_with_duplicate_genres())

    scanner = opdsScanner()
    scanner.processfile(
        fb2_path.name,
        str(tmp_path),
        str(fb2_path),
        None,
        0,
        os.path.getsize(fb2_path),
    )

    book = Book.objects.get(filename=fb2_path.name)
    assert book is not None
    # Ожидаем 2 уникальных жанра (Detective, Sci-Fi), несмотря на 3 тега <genre>
    assert book.genres.count() == 2
