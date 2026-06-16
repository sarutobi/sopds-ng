"""Интеграционные тесты: Django, БД, файловая система, Constance."""

import pytest


def pytest_collection_modifyitems(config, items):
    for item in items:
        item.add_marker(pytest.mark.integration)
