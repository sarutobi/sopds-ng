"""Сервисы для работы со статистическими счетчиками."""

from opds_catalog.models import (
    Counter,
    counter_allcatalogs,
    counter_allbooks,
    counter_allauthors,
    counter_allgenres,
    counter_allseries,
)


def get_counter(counter_name: str) -> int:
    """Возвращает значение счетчика.

    :param counter_name: Наименование счетчика
    :type counter_name: str

    :returns: значение запрошенного счетчика
    :rtype: int
    """
    return Counter.objects.get_counter(counter_name)


def get_catalogs_count() -> int:
    """Возвращает количество каталогов."""
    return get_counter(counter_allcatalogs)


def get_books_count() -> int:
    """Возвращает количество книг."""
    return get_counter(counter_allbooks)


def get_authors_count() -> int:
    """Возвращает количество авторов."""
    return get_counter(counter_allauthors)


def get_genres_count() -> int:
    """Возвращает количество жанров."""
    return get_counter(counter_allgenres)


def get_series_count() -> int:
    """Возвращает количество серий."""
    return get_counter(counter_allseries)
