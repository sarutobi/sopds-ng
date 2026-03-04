"""Фикстуры для фидов opds."""

import os
from lxml import etree

from django.contrib.auth.models import AnonymousUser


from opds_catalog.feeds import MainFeed, GenresFeed
import pytest


@pytest.fixture
def main_feed() -> MainFeed:
    """Формирование главного фида."""
    return MainFeed()


@pytest.fixture
def genres_feed() -> GenresFeed:
    """Фид жанров."""
    feed = GenresFeed()
    return feed


@pytest.fixture
def opds_1_1(test_rootlib):
    relaxng_doc = etree.parse(os.path.join(test_rootlib, "opds1.1.rng"))
    return relaxng_doc
