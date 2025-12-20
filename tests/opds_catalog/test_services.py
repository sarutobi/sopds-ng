# Тесты для сервисов opds_catalog

import pytest
from opds_catalog.services import extract_fb2_cover, unzip_fb2_service


@pytest.mark.django_db
def test_extract_fb2_cover_service(fb2_book_from_fs) -> None:
    """Тест получения обложки из книги fb2"""
    cover = extract_fb2_cover(fb2_book_from_fs, "", "")
    assert cover is not None
    assert len(cover) == 56360


@pytest.mark.parametrize(
    "f_data, f_expected",
    [
        ("fb2_book_from_fs", "fb2_book_from_fs"),
        ("zipped_fb2_book_from_fs", "fb2_book_from_fs"),
    ],
)
def test_unzip_fb2_service(f_data, f_expected, request) -> None:
    data = request.getfixturevalue(f_data)
    expected = request.getfixturevalue(f_expected)
    actual = unzip_fb2_service(data)
    assert actual.getvalue() == expected.getvalue()
