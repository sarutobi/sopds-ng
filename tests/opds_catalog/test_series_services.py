"""Тесты сервисов серий series_services."""

import pytest

from tests.fixtures.model_fixtures import (  # noqa: F401
    book_with_relations,
    series,
    update_counters,
)

from opds_catalog.models import Series
from opds_catalog.services import series_services


pytestmark = pytest.mark.django_db


class TestSeriesServices:
    """Тесты методов series_services."""

    def test_search_series_by_exact(self, book_with_relations):
        """Поиск серии по точному совпадению."""
        results = series_services.search_series("e", "mywork", author_id=None)
        assert results.count() == 1
        assert results[0].ser == "mywork"

    def test_search_series_by_begin(self, book_with_relations):
        """Поиск серии по началу названия."""
        results = series_services.search_series("b", "myw", author_id=None)
        assert results.count() == 1

    def test_search_series_without_results(self):
        """Поиск несуществующей серии."""
        results = series_services.search_series("e", "nonexist", author_id=None)
        assert results.count() == 0

    def test_get_series_with_chars(self, book_with_relations):
        """Получение списка серий по шаблону и длине."""
        # После создания книги с серией, get_series должен вернуть как минимум одну серию
        results = series_services.get_series("", 1, lang_code=0)
        assert len(results) > 0
        assert results[0].id == "M"  # первая буква (заглавная)
        assert results[0].cnt > 0

    def test_get_series_longer(self, book_with_relations):
        """Продвинутый поиск серий с большей длиной."""
        results = series_services.get_series("MYWO", 5, lang_code=0)
        assert len(results) == 1
        assert results[0].id == "MYWOR"  # первые 5 символов
        assert results[0].cnt == 1
