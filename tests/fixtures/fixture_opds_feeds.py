"""Фикстуры для фидов opds."""

import os

from lxml import etree
import pytest

from opds_catalog.feeds import GenresFeed, MainFeed


@pytest.fixture
def main_feed() -> MainFeed:
    """Формирование главного фида.

    Экземпляр ``MainFeed`` — главный OPDS-фид. Используется для проверки структуры и
    содержимого корневого фида.

    :scope: function
    :returns: MainFeed
    :rtype: opds_catalog.feeds.MainFeed
    """
    return MainFeed()


@pytest.fixture
def genres_feed() -> GenresFeed:
    """Фид жанров.

    Экземпляр ``GenresFeed`` — фид по жанрам.

    :scope: function
    :returns: GenresFeed
    :rtype: opds_catalog.feeds.GenresFeed
    """
    feed = GenresFeed()
    return feed


@pytest.fixture
def opds_1_1(test_rootlib):
    """Грамматика для OPDS версии 1.1.

    Загружает RelaxNG-грамматику для OPDS версии 1.1 из тестовой директории.
    Возвращает ``lxml.etree.RelaxNG``.

    :scope: function
    :returns: RelaxNG
    :rtype: lxml.etree.RelaxNG
    """
    relaxng_doc = etree.parse(os.path.join(test_rootlib, "opds1.1.rng"))
    return relaxng_doc


@pytest.fixture
def opds_1_2(test_rootlib):
    """Грамматика для OPDS версии 1.2.

    Загружает RelaxNG-грамматику для OPDS версии 1.2.

    :scope: function
    :returns: RelaxNG
    :rtype: lxml.etree.RelaxNG
    """
    relaxng_doc = etree.parse(os.path.join(test_rootlib, "opds1.2.rng"))
    return relaxng_doc
