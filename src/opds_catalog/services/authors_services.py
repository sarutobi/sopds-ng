"""Сервисы для работы с авторами."""

from typing import TypedDict

from django.db.models import (
    CharField,
    Count,
    F,
    Func,
    IntegerField,
    QuerySet,
    Value,
)
from django.utils.translation import gettext_lazy as _

from opds_catalog.models import Author
from opds_catalog.services import SearchType


class AuthorTemplateResult(TypedDict):
    sid: str
    template_length: int
    cnt: int


def find_authors_by_template(
    chars: str, length: int, lang_code: int | None
) -> QuerySet:
    """Поиск авторов по шаблону.

    Выполняется поиск авторов, фамилии которых начинаются с указанного шаблона.
    :param chars: Шаблон начала фамилии автора.
    :type chars: str
    :param length: Длина шаблона.
    :type length: int
    :param lang_code: код языка, на котором ведется поиск.
    :type lang_code: int|None

    :returns: Запрос для поиска авторов по шаблону.
    :rtype: QuerySet
    """
    query = (
        Author.objects.filter(search_full_name__startswith=chars)
        .annotate(
            template_length=Value(length, output_field=IntegerField()),
            sid=Func(
                F("search_full_name"),
                1,
                length,
                function="SUBSTR",
                output_field=CharField(),
            ),
        )
        .values("sid", "template_length")
        .annotate(cnt=Count("sid"))
        .order_by("sid")
    )
    if lang_code:
        query = query.filter(lang_code=lang_code)

    return query


def search_authors(searchtype: SearchType, searchterms: str) -> QuerySet[Author]:
    """Поиск авторов.

    :param searchtype: Тип поиска (один из значений SearchType).
    :type searchtype: SearchType

    :param searchterms: Строка для поиска.
    :type searchterms: str

    :returns: Запрос с авторами, соответствующими критериям поиска.
    :rtype: QuerySet[Author]

    :raises ValueError: Если передан неподдерживаемый тип поиска.
    """
    search_terms_upper = searchterms.upper()
    if searchtype == SearchType.BY_SUBSTRING:
        authors = Author.objects.filter(
            search_full_name__contains=search_terms_upper
        ).order_by("search_full_name")
    elif searchtype == SearchType.BY_START_WITH:
        authors = Author.objects.filter(
            search_full_name__startswith=search_terms_upper
        ).order_by("search_full_name")
    elif searchtype == SearchType.BY_EXACT_MATCH:
        authors = Author.objects.filter(search_full_name=search_terms_upper).order_by(
            "search_full_name"
        )
    else:
        raise ValueError(f"Unsupported search type: {searchtype}")
    return authors


def search_authors_with_counts(
    searchtype: SearchType, searchterms: str
) -> QuerySet[Author]:
    """Поиск авторов с подсчетом количества книг.

    :param searchtype: Тип поиска (один из значений SearchType).
    :type searchtype: SearchType

    :param searchterms: Строка для поиска.
    :type searchterms: str

    :returns: Запрос с авторами, соответствующими критериям поиска,
              с аннотированным количеством книг (book_count).
    :rtype: QuerySet[Author]

    :raises ValueError: Если передан неподдерживаемый тип поиска.
    """
    search_terms_upper = searchterms.upper()
    queryset = Author.objects.all()

    if searchtype == SearchType.BY_SUBSTRING:
        queryset = queryset.filter(search_full_name__contains=search_terms_upper)
    elif searchtype == SearchType.BY_START_WITH:
        queryset = queryset.filter(search_full_name__startswith=search_terms_upper)
    elif searchtype == SearchType.BY_EXACT_MATCH:
        queryset = queryset.filter(search_full_name=search_terms_upper)
    else:
        raise ValueError(f"Unsupported search type: {searchtype}")

    queryset = queryset.annotate(book_count=Count("book")).order_by("search_full_name")
    return queryset


def get_author_name(author_id: int) -> str:
    """Возвращает полное имя автора по его ID.

    :param author_id: Идентификатор автора.
    :type author_id: int

    :returns: Полное имя автора или сообщение "Author not found".
    :rtype: str

    :raises: Не вызывает исключения, возвращает строку в случае отсутствия автора.
    """
    try:
        author = Author.objects.get(id=author_id)
        return author.full_name
    except Author.DoesNotExist:
        return _("Author not found")
