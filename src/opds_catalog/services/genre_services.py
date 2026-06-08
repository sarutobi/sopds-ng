"""Сервисы работы с жанрами."""

from typing import Any

from django.db.models import Count, Min, QuerySet

from opds_catalog.models import Genre


def get_genres() -> QuerySet[Genre, dict[str, Any]]:
    """Возвращает список жанров с количеством книг в каждом жанре."""
    return (
        Genre.objects.values("section")
        .annotate(section_id=Min("id"), num_book=Count("book"))
        .filter(num_book__gt=0)
        .order_by("section")
    )


def get_genre_details(id: int) -> QuerySet[Genre, dict[str, Any]]:
    """Возвращает список поджанров жанра и количество книг в нем."""
    section = get_genre_section(id)
    return (
        Genre.objects.filter(section=section)
        .annotate(num_book=Count("book"))
        .filter(num_book__gt=0)
        .values()
        .order_by("subsection")
    )


def get_genre_section(id: int) -> str:
    """Возвращает наименование жанра."""
    return Genre.objects.get(id=id).section
