"""Фикстуры для фидов OPDS."""

from opds_catalog.feeds import MainFeed

import pytest


@pytest.fixture
def main_feed(django_db) -> str:
    """Формирование главного фида."""
    return MainFeed().writeString("UTF-8")
