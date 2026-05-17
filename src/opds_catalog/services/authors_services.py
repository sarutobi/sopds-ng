"""Сервисы для работы с авторами."""

from typing import Any

from opds_catalog.models import Author
from opds_catalog.utils import to_int
from django.db.models import (
    Model,
    F,
    Func,
    Value,
    IntegerField,
    CharField,
    Count,
    QuerySet,
)

from django.utils.translation import gettext_lazy as _
from opds_catalog.services import SearchType


def find_authors_by_template(
    chars: str, length: int, lang_code: int | None
) -> QuerySet[Author, dict[str, Any]]:
    """Поиск авторов по шаблону.

    Выполняетcя поиcк авторов, фамилии которых начинаются с указанного шаблона.
    :param chars: Шаблон начала фамилии автора.
    :type chars: str
    :param lenth: Длина шаблона.
    :type length: int
    :param lang_code: код языка, на котором ведется поиск.
    :type lang_code: int|None

    :returns: Запрос для поиска автров по шаблону.
    :rtype: QuerySet[Author,dict[str, Any]]
    """
    query = (
        Author.objects.filter(search_full_name__startswith=chars)
        .annotate(
            l=Value(length, output_field=IntegerField()),
            sid=Func(
                F("search_full_name"),
                1,
                length,
                function="SUBSTR",
                output_field=CharField(),
            ),
        )
        .values("sid", "l")
        .annotate(cnt=Count("sid"))
        .order_by("sid")
    )
    if lang_code:
        query = query.filter(lang_code=lang_code)

    return query


def search_authors(searchtype: str, searchterms: str) -> QuerySet[Author, Author]:
    """Поиск авторов."""
    if searchtype == SearchType.BySubstring:
        authors = Author.objects.filter(
            search_full_name__contains=searchterms.upper()
        ).order_by("search_full_name")
    elif searchtype == SearchType.ByStartWith:
        authors = Author.objects.filter(
            search_full_name__startswith=searchterms.upper()
        ).order_by("search_full_name")
    elif searchtype == SearchType.ByExactMatch:
        authors = Author.objects.filter(search_full_name=searchterms.upper()).order_by(
            "search_full_name"
        )
    return authors


def get_author_name(id: str) -> str:
    a_id = to_int(id)
    try:
        a_name = Author.objects.get(a_id).full_name
    except Model.DoesNotExist:
        a_name = _("Author not found")
    return a_name
