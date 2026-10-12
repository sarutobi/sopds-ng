"""Тесты функции addseries сервиса сканера на некорректных входных данных."""

import pytest

from opds_catalog.models import Series
from opds_catalog.services.scanner import addseries

pytestmark = pytest.mark.django_db


def test_addseries_none() -> None:
    """addseries(None) не должен падать и не должен создавать запись."""
    assert addseries(None) is None
    assert Series.objects.count() == 0


def test_addseries_empty_string() -> None:
    """addseries('') не должен создавать пустую серию."""
    assert addseries("") is None
    assert Series.objects.count() == 0


def test_addseries_valid() -> None:
    """Корректное название серии создаётся и повторно не дублируется."""
    ser = addseries("My Series")
    assert ser is not None
    assert ser.ser == "My Series"
    assert addseries("My Series") is ser or Series.objects.count() == 1
