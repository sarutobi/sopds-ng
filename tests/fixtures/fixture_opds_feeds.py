"""Фикстуры для фидов opds."""

from django.contrib.auth.models import AnonymousUser


from opds_catalog.feeds import GenresFeed
import pytest


@pytest.fixture
def genres_feed() -> GenresFeed:
    """Фид жанров."""
    feed = GenresFeed()
    return feed
