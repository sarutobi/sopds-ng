"""Unit-тесты: без Django, без БД, без HTTP.

Фикстуры из ``tests/conftest.py`` (BytesIO, ZIP-тесты) доступны.
Фикстуры из ``tests/fixtures/`` не требуются — они для Django.
"""

import pytest


def pytest_collection_modifyitems(config, items):
    for item in items:
        item.add_marker(pytest.mark.unit)
