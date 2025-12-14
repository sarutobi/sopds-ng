# Тесты для сервисов opds_catalog

import pytest
from opds_catalog.services import extract_fb2_cover


@pytest.mark.django_db
def test_extract_fb2_cover_service(fb2_book_from_fs) -> None:
    """Тест получения обложки из книги fb2"""
    cover = extract_fb2_cover(fb2_book_from_fs, None, None)
    assert cover is not None
