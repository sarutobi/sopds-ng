"""Утилиты для работы с пагинацией в OPDS-фидах."""

from __future__ import annotations

from django.core.paginator import Page


def paginator_to_dict(page: Page) -> dict:
    """Преобразует Django Paginator Page в словарь для OPDS-фида.

    Возвращает dict с ключами: num_pages, has_previous, has_next,
    previous_page_number, next_page_number, number, page_range.

    :param page: Страница из django.core.paginator.Paginator.
    :returns: Словарь с метаданными пагинации.
    """
    paginator = page.paginator
    return {
        "num_pages": paginator.num_pages,
        "has_previous": page.has_previous(),
        "has_next": page.has_next(),
        "previous_page_number": page.previous_page_number()
        if page.has_previous()
        else 1,
        "next_page_number": page.next_page_number()
        if page.has_next()
        else paginator.num_pages,
        "number": page.number,
        "page_range": list(paginator.page_range),
    }
