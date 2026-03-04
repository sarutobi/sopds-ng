"""Сервисные функции для работы с книгами."""

from django.db.models import Q


def find_by_title_contains(filter: str) -> Q:
    """Поиск книг по названию, содержащему подстроку."""
    return Q(search_title__contains=filter.upper())


def find_by_title_startswith(filter: str) -> Q:
    """Поиск книг по названию, начинающемуся на подстроку."""
    return Q(search_title__startswith=filter.upper())


def find_by_title(filter: str) -> Q:
    """Поиск книги по названию."""
    return Q(search_title=filter.upper())


def find_by_author(filter: int) -> Q:
    """Поиск книги по автору."""
    return Q(authors=filter)


def find_by_series(filter: int) -> Q:
    """Поиск книг по серии."""
    return Q(series=filter)


def find_by_genre(filter: int) -> Q:
    """Поиск книг по жанру."""
    return Q(genres=filter)


def find_by_bookshelf(filter) -> Q:
    """Поиск книг на полке пользователя."""
    return Q(bookshelf__user=filter)
