"""Сервисы для работы с сериями."""

from django.db.models.query import RawQuerySet
from django.db.models import Count
from opds_catalog.models import Series


def get_series(chars: str, length: int, lang_code: int | None = None) -> RawQuerySet:
    """Запрос перечня серий, начинающихся с определенного набора символов.

    :param chars: Набор символов, с которого должна начинаться серия.
    :type chars: str
    :param length: длина набора символов, который надо найти.
    :type length: int
    :param lang_code: Опциональный параметр языка для серии.
    :type lang_code: int|None

    :returns: "Сырой" запрос данных.
    :rtype: RawQuerySet
    """
    if lang_code:
        sql = """select %(length)s as l, substring(search_ser,1,%(length)s) as id,
        count(*) as cnt 
                from opds_catalog_series 
                where lang_code=%(lang_code)s and search_ser like '%(chars)s%%%%'
                group by substring(search_ser,1,%(length)s) 
                order by id""" % {
            "length": length,
            "lang_code": lang_code,
            "chars": chars,
        }
    else:
        sql = """select %(length)s as l, substring(search_ser,1,%(length)s) as id,
        count(*) as cnt 
                from opds_catalog_series 
                where search_ser like '%(chars)s%%%%'
                group by substring(search_ser,1,%(length)s) 
                order by id""" % {"length": length, "chars": chars}

    dataset = Series.objects.raw(sql)
    return dataset


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
