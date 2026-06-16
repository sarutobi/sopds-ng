"""Acceptance-тесты: HTTP-клиент, полный стек Django, фиды, сериализация."""

import pytest


def pytest_collection_modifyitems(config, items):
    for item in items:
        item.add_marker(pytest.mark.acceptance)
