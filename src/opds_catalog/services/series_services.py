"""Сервисы для работы с сериями."""

from typing import Any

from django.db.models import Count, IntegerField, QuerySet, Value
from django.db.models.functions import Substr
from django.utils.translation import gettext as _

from opds_catalog.models import Series
from opds_catalog.utils import to_int


def get_series(chars: str, length: int, lang_code: int | None = None) -> QuerySet:
    """Запрос перечня серий, начинающихся с определённого набора символов.

    :param chars: Набор символов, с которого должна начинаться серия.
    :param length: Длина набора символов для группировки.
    :param lang_code: Опциональный код языка для фильтрации.
    :returns: Запрос для поиска серий по шаблону.
    """
    series = (
        Series.objects.filter(search_ser__startswith=chars)
        .annotate(
            l=Value(length, output_field=IntegerField()),
            sid=Substr("search_ser", 1, length),
        )
        .values("l", "sid")
        .annotate(cnt=Count("sid"))
        .order_by("sid")
    )
    if lang_code:
        series = series.filter(lang_code=lang_code)

    return series


def search_series(searchtype: str, searchterms: str, author_id: int | None = None):
    """Поиск по сериям."""
    if searchtype == "m":
        series = Series.objects.filter(search_ser__contains=searchterms.upper())
    elif searchtype == "b":
        series = Series.objects.filter(search_ser__startswith=searchterms.upper())
    elif searchtype == "e":
        series = Series.objects.filter(search_ser=searchterms.upper())
    elif searchtype == "a":
        series = Series.objects.filter(book__authors=author_id)

    return series.annotate(count_book=Count("book")).distinct().order_by("search_ser")


def get_series_name(id: Any) -> str:
    """Возвращает наименование серии."""
    ser_id = to_int(id)
    try:
        ser_name = Series.objects.get(id=ser_id).ser
    except Series.DoesNotExist:
        ser_name = _("Series not found")
    return ser_name
