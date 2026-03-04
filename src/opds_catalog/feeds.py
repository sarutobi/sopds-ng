"""Описание OPDS фидов."""

from opds_catalog.services import book_services

import datetime
from dataclasses import dataclass
from typing import Any

from constance import config
from django.contrib.syndication.views import Feed
from django.db.models import CharField, Count, F, Func, IntegerField, Min, Value, Q
from django.http import HttpRequest
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.feedgenerator import Atom1Feed, Enclosure, rfc3339_date
from django.utils.html import strip_tags
from django.utils.translation import gettext as _

from book_tools.format import mime_detector
from book_tools.format.mimetype import Mimetype
from opds_catalog import models, settings
from opds_catalog.models import (
    Author,
    Book,
    Genre,
    Series,
)

# from opds_catalog.middleware import BasicAuthMiddleware
from opds_catalog.opds_paginator import Paginator as OPDS_Paginator
from opds_catalog.services.catalog_services import paginated_catalog_content
from opds_catalog.storage import (
    get_bookshelf_books_count,
    get_catalog_by_id,
    get_counter,
    get_root_catalog,
)

from .decorators import sopds_auth_validate


@dataclass
class OPDSLinkType:
    """Типы OPDS ссылок."""

    Navigation = "application/atom+xml;profile=opds-catalog;kind=navigation"
    Acquisition = "application/atom+xml;profile=opds-catalog;kind=acquisition"


@dataclass
class OPDSSearchType:
    """Возможные варианты поиска книг в каталоге."""

    ByTitleSubstring = "m"
    ByTitleStartWith = "b"
    ByTitleExact = "e"
    ByAuthor = "a"
    BySeries = "s"
    ByAuthorAndSeries = "as"
    ByGenre = "g"
    ByUser = "u"
    Doubles = "d"


class AuthFeed(Feed):
    """OPDS фид с авторизацией."""

    # request: HttpRequest = None

    @sopds_auth_validate
    def __call__(self, request: HttpRequest, *args, **kwargs):
        """Переопределение метода для возможности работы с авторизацией.

        Сохраняет поступивший запрос в отдельном поле класса

        :param request: поступивший запрос
        :type: request: HttpRequest
        """
        self.request = request

        return super().__call__(request, *args, **kwargs)

    def feed_extra_kwargs(self, obj):
        """Дополнительные атрибуты фида."""
        return {
            "searchTerm_url": reverse("opds_catalog:opensearch"),
            "start_url": reverse("opds_catalog:main"),
            "description_mime_type": "text",
        }

    def _to_int(self, val: Any, default: int = 0) -> int:
        try:
            result = int(val)
            return result
        except Exception:
            return default


class opdsEnclosure(Enclosure):
    """Расширение стандартного класса Enclosure для OPDS."""

    def __init__(self, url: str, mime_type: str, rel: str):
        """Дополнительно сохраняет внутри объекта  параметр rel."""
        self.rel = rel
        super(opdsEnclosure, self).__init__(url, 0, mime_type)


class NavigationFeed(Atom1Feed):
    """Класс представляет иерархию фидов.

    Согласно спецификации OPDS Catalog 1.1 этот класс предоставляет
    просматриваемую иерархию других OPDS каталогов и ресурсов.
    Этот объект на может содержать ссылки на элементы OPDS каталога,
    он содержит только ссылки на другие NavigationFeeds или AcquisitionFeeds.
    """

    def item_attributes(self, item):
        """Согласно RFC2119 устанавливается атрибут type(SHOULD)."""
        attrs = super().item_attributes(item)
        attrs["type"] = OPDSLinkType.Navigation


class AcquisitionFeed(Atom1Feed):
    """Класс представляет множество сущностей OPDS каталога.

    Согласно специффикации OPDS Catalog 1.1 этот класс предоставляет
    доступ к элеметнам OPDS каталога.
    """

    # RFC2119 SHOULD
    type: str = OPDSLinkType.Acquisition


class PaginatorMixin:
    """Обработка параметров пейджера."""

    def catalog_pages_parameters(paginator: dict, id) -> tuple[str | None, str | None]:
        """Формирование параметров пейджинга для фида каталога."""
        if paginator["has_previous"]:
            prev_url = reverse(
                "opds_catalog:cat_page",
                kwargs={"cat_id": id, "page": paginator["previous_page_number"]},
            )
        else:
            prev_url = None

        if paginator["has_next"]:
            next_url = reverse(
                "opds_catalog:cat_page",
                kwargs={"cat_id": id, "page": paginator["next_page_number"]},
            )
        else:
            next_url = None

        return prev_url, next_url

    def get_prev_next_urls(
        self, viewname: str, obj: dict
    ) -> tuple[str | None, str | None]:
        """Параметры пейджинга.

        Формирует параметры для перехода на предыдущую и следующую страницы для представления.

        :param viewname: Наименование представления
        :type viewname: str

        :param obj: Параметры запроса, которые были переданы представлению
        :type obj: dict

        :returns: ссылки на следующую и предыдущую страницы данных или None
        :rtype: tuple[str|None, str|None]
        """
        if obj["paginator"]["has_previous"]:
            prev_url = reverse(
                viewname,
                kwargs={
                    "searchtype": obj["searchtype"],
                    "searchterms": obj["searchterms"],
                    "page": (obj["paginator"]["previous_page_number"]),
                },
            )
        else:
            prev_url = None

        if obj["paginator"]["has_next"]:
            next_url = reverse(
                "opds_catalog:searchseries",
                kwargs={
                    "searchtype": obj["searchtype"],
                    "searchterms": obj["searchterms"],
                    "page": (obj["paginator"]["next_page_number"]),
                },
            )
        else:
            next_url = None
        return prev_url, next_url


class opdsFeed(Atom1Feed):
    """Базовый класс для фида opds."""

    content_type = "application/atom+xml; charset=utf-8"

    def root_attributes(self) -> dict[str, str]:
        """Пространства имен фида."""
        return {
            "xmlns": "http://www.w3.org/2005/Atom",
            "xmlns:dcterms": "http://purl.org/dc/terms",
        }

    def _add_link(
        self,
        handler,
        href,
        rel: str | None = None,
        type: str | None = None,
        title: str | None = None,
    ) -> None:
        attrs = {"href": href}
        if rel is not None:
            attrs["rel"] = rel
        if type is not None:
            attrs["type"] = type
        if title is not None:
            attrs["title"] = title

        handler.addQuickElement("link", None, attrs)

    def _set_feed_link(self, handler):
        if self.feed.get("link") is not None:
            self._add_link(
                handler,
                self.feed.get("link"),
                "self",
                OPDSLinkType.Navigation,
            )

    def _set_pager_links(self, handler):
        if self.feed.get("prev_url") is not None:
            self._add_link(
                handler,
                self.feed["prev_url"],
                "prev",
                "application/atom+xml;profile=opds-catalog",
                "Previous Page",
            )
            handler.characters("\n")
        if self.feed.get("next_url") is not None:
            self._add_link(
                handler,
                self.feed["next_url"],
                "next",
                "application/atom+xml;profile=opds-catalog",
                "Next Page",
            )
            handler.characters("\n")

    def add_root_elements(self, handler) -> None:
        """Формирует корневой элемент фида."""
        handler._short_empty_elements = True
        # super(opdsFeed, self).add_root_elements(handler)
        # Base feed items
        handler.addQuickElement("id", self.feed["id"])
        handler.addQuickElement("icon", settings.ICON)
        handler.addQuickElement("title", self.feed["title"])
        handler.characters("\n")
        if self.feed.get("subtitle") is not None:
            handler.addQuickElement("subtitle", self.feed["subtitle"])
        handler.addQuickElement("updated", rfc3339_date(self.latest_post_date()))
        handler.characters("\n")
        # Links
        self._set_feed_link(handler)
        if self.feed.get("start_url") is not None:
            self._add_link(
                handler, self.feed["start_url"], "start", OPDSLinkType.Navigation
            )
            handler.characters("\n")
        self._set_pager_links(handler)
        if self.feed.get("search_url") is not None:
            self._add_link(
                handler, self.feed["search_url"], "search", OPDSLinkType.Navigation
            )

            handler.characters("\n")
        if self.feed.get("searchTerm_url") is not None:
            self._add_link(
                handler,
                self.feed["searchTerm_url"],
                "search",
                "application/opensearchdescription+xml",
            )
            handler.characters("\n")

    def _item_authors(self, handler, item):
        if item.get("authors") is not None:
            for a in item["authors"]:
                handler.startElement("author", {})
                handler.addQuickElement("name", a["full_name"])
                # handler.addQuickElement("uri", item['author_link'])
                handler.endElement("author")
                self._add_link(
                    handler,
                    href=reverse(
                        "opds_catalog:searchbooks",
                        kwargs={"searchtype": "a", "searchterms": a["id"]},
                    ),
                    rel="related",
                    type="application/atom+xml;profile=opds-catalog",
                    title=_("All books by %(author)s") % {"author": a["full_name"]},
                )
                handler.characters("\n")

    def _item_genres(self, handler, item):
        if item.get("genres") is not None:
            for g in item["genres"]:
                handler.addQuickElement(
                    "category", "", {"term": g["subsection"], "label": g["subsection"]}
                )
            handler.characters("\n")

    def _item_content_type(self, handler, item):
        if self.feed.get("description_mime_type") is not None:
            content_type = self.feed["description_mime_type"]
        else:
            content_type = "text/html"
        if item.get("description") is not None:
            handler.addQuickElement(
                "content", item["description"], {"type": content_type}
            )
            handler.characters("\n")

    def add_item_elements(self, handler, item):
        disable_item_links = item.get("disable_item_links")
        handler.characters("\n")
        handler.addQuickElement("id", item["unique_id"])
        handler.characters("\n")
        handler.addQuickElement("title", item["title"])
        handler.characters("\n")
        if not disable_item_links:
            self._add_link(handler, item["link"], "alternate")
            handler.characters("\n")
        # Enclosures.
        if not disable_item_links and item.get("enclosures") is not None:
            for enclosure in item["enclosures"]:
                self._add_link(
                    handler, enclosure.url, enclosure.rel, enclosure.mime_type
                )
                handler.characters("\n")

        if item.get("updateddate") is not None:
            handler.addQuickElement("updated", rfc3339_date(item["updateddate"]))
            handler.characters("\n")

        self._item_content_type(handler, item)

        self._item_authors(handler, item)

        self._item_genres(handler, item)

        if item.get("doubles") is not None:
            self._add_link(
                handler,
                href=reverse(
                    "opds_catalog:searchbooks",
                    kwargs={"searchtype": "d", "searchterms": item["doubles"]},
                ),
                rel="related",
                type="application/atom+xml;profile=opds-catalog",
                title=_("Book doublicates"),
            )
            handler.characters("\n")


class MainFeed(AuthFeed):
    """Корневой фид."""

    feed_type = opdsFeed
    title: str = settings.TITLE
    subtitle: str = settings.SUBTITLE

    def link(self):
        """Ссылка на корневой фид."""
        return reverse("opds_catalog:main")

    def items(self):
        """Элементы фида."""
        mainitems = [
            {
                "id": 1,
                "title": _("By catalogs"),
                "link": "opds_catalog:catalogs",
                "descr": _("Catalogs: %(catalogs)s, books: %(books)s."),
                "counters": {
                    "catalogs": get_counter(models.counter_allcatalogs),
                    "books": get_counter(models.counter_allbooks),
                },
            },
            {
                "id": 2,
                "title": _("By authors"),
                "link": (
                    "opds_catalog:lang_authors"
                    if config.SOPDS_ALPHABET_MENU
                    else "opds_catalog:nolang_authors"
                ),
                "descr": _("Authors: %(authors)s."),
                "counters": {"authors": get_counter(models.counter_allauthors)},
            },
            {
                "id": 3,
                "title": _("By titles"),
                "link": (
                    "opds_catalog:lang_books"
                    if config.SOPDS_ALPHABET_MENU
                    else "opds_catalog:nolang_books"
                ),
                "descr": _("Books: %(books)s."),
                "counters": {"books": get_counter(models.counter_allbooks)},
            },
            {
                "id": 4,
                "title": _("By genres"),
                "link": "opds_catalog:genres",
                "descr": _("Genres: %(genres)s."),
                "counters": {"genres": get_counter(models.counter_allgenres)},
            },
            {
                "id": 5,
                "title": _("By series"),
                "link": (
                    "opds_catalog:lang_series"
                    if config.SOPDS_ALPHABET_MENU
                    else "opds_catalog:nolang_series"
                ),
                "descr": _("Series: %(series)s."),
                "counters": {"series": get_counter(models.counter_allseries)},
            },
        ]
        # TODO: Сюда мы можем попасть либо если выключена авторизация либо если
        # авторизация включена и пользователь авторизован.
        if config.SOPDS_AUTH and self.request.user.is_authenticated:
            mainitems += [
                {
                    "id": 6,
                    "title": _("%(username)s Book shelf")
                    % ({"username": self.request.user.username}),  # ty: ignore[unresolved-attribute]
                    "link": "opds_catalog:bookshelf",
                    "descr": _("%(username)s books readed: %(bookshelf)s."),
                    "counters": {
                        "bookshelf": get_bookshelf_books_count(user=self.request.user),  # ty: ignore [invalid-argument-type]
                        "username": self.request.user.username,  # ty: ignore [unresolved-attribute]
                    },
                },
            ]

        return mainitems

    def item_link(self, item):
        """Ссылка на элемент фида."""
        return reverse(item["link"])

    def item_title(self, item):
        """Заголовок элемента фида."""
        return item["title"]

    def item_description(self, item):
        """Описание элемента фида."""
        return item["descr"] % item["counters"]

    def item_guid(self, item):
        """Уникальный идентификатор элемента фида."""
        return "m:%s" % item["id"]

    def item_updateddate(self):
        """Время обновления фида."""
        return timezone.now()

    def item_enclosures(self, item):
        """Вложения в элемент фида."""
        return (
            opdsEnclosure(
                self.item_link(item),
                OPDSLinkType.Navigation,
                "subsection",
            ),
        )

    def item_extra_kwargs(self, item):
        """Дополнительные атрибуты элемента фида."""
        disable_item_links = list(item["counters"].values())[0] == 0
        return {"disable_item_links": disable_item_links}


class CatalogsFeed(AuthFeed):
    """Навигационный фид каталогов."""

    feed_type = opdsFeed
    subtitle = settings.SUBTITLE

    def get_object(self, request, cat_id: int | None = None, page: int = 1):  # ty:ignore [invalid-method-override]
        """Выборка каталогов для отображения в фиде.

        :param request: Поступивший от клиента запрос на построение фида
        :type request: HttpRequest

        :param cat_id: Идентификатор каталога. Если параметр не задан, то будет
        возвращен корневой каталог.
        :type cat_id: int | None

        :param page: Номер страницы для пейджинга. По умолчанию - 1
        :type page: int

        :returns: Содержимое каталога (подкаталоги и книги), метаданные текущего
        каталога, метаданные пейджера.
        :rtype: list[list[Catalog], list[Book]], Catalog, OPDS_Paginator
        """
        page_num = self._to_int(page, default=1)

        root_cat = (
            get_catalog_by_id(cat_id) if cat_id is not None else get_root_catalog()
        )
        items, pager_data = paginated_catalog_content(
            root_cat, page_num, config.SOPDS_MAXITEMS
        )

        return items, root_cat, pager_data

    def title(self, obj) -> str:
        """Заголовок фида."""
        items, cat, paginator = obj
        if cat.parent:
            return f"{settings.TITLE} | {_('By catalogs')} | {cat.path}"
        else:
            return f"{settings.TITLE} | {_('By catalogs')}"

    def link(self, obj):
        """Ссылка на каталог."""
        _, cat, paginator = obj
        return reverse(
            "opds_catalog:cat_page",
            kwargs={"cat_id": cat.id, "page": paginator["number"]},
        )

    def feed_extra_kwargs(self, obj):
        _, cat, paginator = obj
        start_url = reverse("opds_catalog:main")
        if paginator["has_previous"]:
            prev_url = reverse(
                "opds_catalog:cat_page",
                kwargs={"cat_id": cat.id, "page": paginator["previous_page_number"]},
            )
        else:
            prev_url = None

        if paginator["has_next"]:
            next_url = reverse(
                "opds_catalog:cat_page",
                kwargs={"cat_id": cat.id, "page": paginator["next_page_number"]},
            )
        else:
            next_url = None

        return {
            "searchTerm_url": reverse("opds_catalog:opensearch"),
            "start_url": start_url,
            "prev_url": prev_url,
            "next_url": next_url,
        }

    def items(self, obj):
        """Элементы фида."""
        items, _, _ = obj
        return items

    def item_title(self, item):
        """Заголовок элемента фида."""
        return item["title"]

    def item_guid(self, item) -> str:
        """Уникальный идентификатор элемента фида."""
        # gp = "c:" if item["is_catalog"] else "b:"
        return f"{item['prefix']}{item['id']}"

    def item_link(self, item):
        """Ссылка на получение объекта элемента фида."""
        if item["is_catalog"]:
            return reverse("opds_catalog:cat_tree", kwargs={"cat_id": item["id"]})
        else:
            return reverse(
                "opds_catalog:download", kwargs={"book_id": item["id"], "zip_flag": 0}
            )

    def item_enclosures(self, item):
        """Вложение в элемент фида."""
        if item["is_catalog"]:
            return [
                opdsEnclosure(
                    reverse("opds_catalog:cat_tree", kwargs={"cat_id": item["id"]}),
                    OPDSLinkType.Navigation,
                    "subsection",
                ),
            ]
        else:
            return self._book_enclosure(item)

    def _book_enclosure(self, book) -> list[opdsEnclosure]:
        mime = Mimetype.mime_by_type(book["format"])
        mimezip = Mimetype.FB2_ZIP if mime == Mimetype.FB2 else "%s+zip" % mime

        enclosure: list[opdsEnclosure] = [
            # Основной файл книги
            opdsEnclosure(
                reverse(
                    "opds_catalog:download",
                    kwargs={"book_id": book["id"], "zip_flag": 0},
                ),
                mime,
                "http://opds-spec.org/acquisition/open-access",
            ),
            # Ссылки на обложку и миниатюру
            opdsEnclosure(
                reverse("opds_catalog:cover", kwargs={"book_id": book["id"]}),
                "image/jpeg",
                "http://opds-spec.org/image",
            ),
            opdsEnclosure(
                reverse("opds_catalog:thumb", kwargs={"book_id": book["id"]}),
                "image/jpeg",
                "http://opds-spec.org/thumbnail",
            ),
        ]
        # Добавляем сжатую версию книги, если это допустимо
        if book["format"] not in settings.NOZIP_FORMATS:
            enclosure.append(
                opdsEnclosure(
                    reverse(
                        "opds_catalog:download",
                        kwargs={"book_id": book["id"], "zip_flag": 1},
                    ),
                    mimezip,
                    "http://opds-spec.org/acquisition/open-access",
                )
            )

        # Ссылки на конвертацию в другой формат
        if (config.SOPDS_FB2TOEPUB != "") and (book["format"] == "fb2"):
            enclosure.append(
                opdsEnclosure(
                    reverse(
                        "opds_catalog:convert",
                        kwargs={"book_id": book["id"], "convert_type": "epub"},
                    ),
                    Mimetype.EPUB,
                    "http://opds-spec.org/acquisition/open-access",
                )
            )
        if (config.SOPDS_FB2TOMOBI != "") and (book["format"] == "fb2"):
            enclosure.append(
                opdsEnclosure(
                    reverse(
                        "opds_catalog:convert",
                        kwargs={"book_id": book["id"], "convert_type": "mobi"},
                    ),
                    Mimetype.MOBI,
                    "http://opds-spec.org/acquisition/open-access",
                )
            )

        return enclosure

    def item_description(self, item):
        """Описание элемента."""
        if item["is_catalog"]:
            return item["title"]
        else:
            s = [
                f"<b> {_('Book name:')}</b> {item['title']}<br/>",
            ]
            if item["authors"]:
                s.append(
                    _(
                        "<b>Authors: </b>%s<br/>"
                        % ", ".join(a["full_name"] for a in item["authors"])
                    )
                )
            if item["genres"]:
                s.append(
                    _(
                        "<b>Genres: </b>%s<br/>"
                        % ", ".join(g["subsection"] for g in item["genres"])
                    )
                )
            if item["series"]:
                s.append(
                    _("<b>Series: </b>%s<br/>")
                    % ", ".join(s["ser"] for s in item["series"])
                )
            if item["ser_no"]:
                s.append(
                    _(
                        "<b>No in Series: </b>%s<br/>"
                        % ", ".join(str(s["ser_no"]) for s in item["ser_no"])
                    )
                )
            s.append(
                _(
                    f"<b>File: </b>{item['filename']}<br/><b>File size: </b>{item['filesize']}<br/><b>Changes date: </b>{item['docdate']}<br/>"
                )
            )
            s.append(f"<p class='book'>{item['annotation']}</p>")
            return "".join(s)

    def item_updateddate(self, item):
        if item["is_catalog"]:
            return datetime.datetime.now()
        else:
            return item["registerdate"]


def OpenSearch(request):
    """Выводим шаблон поиска."""
    return render(request, "opensearch.html")


class SearchTypesFeed(AuthFeed):
    """Поисковый фид."""

    feed_type = opdsFeed
    subtitle = settings.SUBTITLE

    def get_object(self, request, searchterms=""):
        return searchterms.replace("+", " ")

    def link(self, obj):
        return "%s%s" % (reverse("opds_catalog:opensearch"), "{searchTerms}/")

    def items(self, obj):
        return [
            {
                "id": 1,
                "title": _("Search by titles"),
                "term": obj,
                "descr": _("Search books by title"),
                "searchview": "searchbooks",
            },
            {
                "id": 2,
                "title": _("Search by authors"),
                "term": obj,
                "descr": _("Search authors by name"),
                "searchview": "searchauthors",
            },
            {
                "id": 3,
                "title": _("Search series"),
                "term": obj,
                "descr": _("Search series"),
                "searchview": "searchseries",
            },
        ]

    def item_link(self, item):
        if item["id"] in (1, 2, 3):
            return reverse(
                f"opds_catalog:{item['searchview']}",
                kwargs={"searchtype": "m", "searchterms": item["term"]},
            )
        return None

    def item_title(self, item):
        return item["title"]

    def item_description(self, item):
        return item["descr"]

    def item_guid(self, item):
        return "st:%s" % item["id"]

    def item_updateddate(self):
        return timezone.now()

    def item_enclosures(self, item):
        return (
            opdsEnclosure(
                self.item_link(item),
                OPDSLinkType.Navigation,
                "subsection",
            ),
        )


class SearchBooksFeed(AuthFeed):
    """Фид поиска книг."""

    feed_type = opdsFeed
    subtitle = settings.SUBTITLE

    queries = {
        "m": book_services.find_by_title_contains,
        "b": book_services.find_by_title_startswith,
        "e": book_services.find_by_title,
        "a": book_services.find_by_author,
        "s": book_services.find_by_series,
        "g": book_services.find_by_genre,
        "u": book_services.find_by_bookshelf,
    }

    def title(self, obj):
        """Заголовок фида."""
        return "%s | %s (%s)" % (
            settings.TITLE,
            _("Books found"),
            _("doubles hide") if config.SOPDS_DOUBLES_HIDE else _("doubles show"),
        )

    def get_object(  # ty: ignore [invalid-method-override]
        self,
        request,
        searchtype="m",
        searchterms: str | int | None = None,
        searchterms0: int | None = None,
        page=1,
    ):
        """Список объектов для фида."""
        # Проверка и типизация переменных
        page_num = self._to_int(page, 1)

        if searchterms is not None:
            st = str(searchterms)
            order_by: list[str] = ["search_title", "-docdate"]

        if searchtype in (
            OPDSSearchType.ByAuthor,
            OPDSSearchType.BySeries,
            OPDSSearchType.ByGenre,
            OPDSSearchType.ByAuthorAndSeries,
        ):
            st = self._to_int(st)

        if searchtype == OPDSSearchType.ByUser:
            if config.SOPDS_AUTH:
                filter = self.queries.get(searchtype)(request.user)
            else:
                filter = Q(id=0)

        elif searchtype == OPDSSearchType.ByAuthorAndSeries:
            st1 = self._to_int(searchterms0)
            filter = Q(
                self.queries.get(OPDSSearchType.ByAuthor)(st),
                self.queries.get(OPDSSearchType.BySeries)(st1),
            )
        else:
            filter: Q = self.queries.get(searchtype)(st)

        if searchtype in (OPDSSearchType.BySeries, OPDSSearchType.ByAuthorAndSeries):
            order_by.insert(0, "bseries__ser_no")
        if searchtype == OPDSSearchType.ByUser:
            order_by = [
                "-bookshelf__readtime",
            ]
        if searchtype == OPDSSearchType.Doubles:
            book_id = self._to_int(searchterms)
            mbook = Book.objects.get(id=book_id)
            books = (
                Book.objects.filter(
                    title__iexact=mbook.title, authors__in=mbook.authors.all()
                )
                .exclude(id=book_id)
                .order_by("search_title", "-docdate")
            )
        else:
            books = Book.objects.filter(filter).order_by(*order_by)
        # Поиск книг на книжной полке
        # if searchtype == OPDSSearchType.ByUser:
        #     if config.SOPDS_AUTH:
        #         books = Book.objects.filter(bookshelf__user=request.user).order_by(
        #             "-bookshelf__readtime"
        #         )
        #     else:
        #         books = Book.objects.filter(id=0)
        # Поиск дубликатов для книги
        # if searchtype == OPDSSearchType.Doubles:
        #     book_id = self._to_int(searchterms)
        #     mbook = Book.objects.get(id=book_id)
        #     books = (
        #         Book.objects.filter(
        #             title__iexact=mbook.title, authors__in=mbook.authors.all()
        #         )
        #         .exclude(id=book_id)
        #         .order_by("search_title", "-docdate")
        #     )

        # prefetch_related on sqlite on items >999 therow error "too many SQL variables"
        # if len(books)>0:
        # books = books.prefetch_related('authors','genres','series').order_by('title','authors','-docdate')

        # Фильтруем дубликаты
        books_count = books.count()
        op = OPDS_Paginator(books_count, 0, page_num, config.SOPDS_MAXITEMS)
        items = []

        prev_title = ""
        prev_authors_set = set()

        # Начаинам анализ с последнего элемента на предидущей странице, чторбы он "вытянул" с этой страницы
        # свои дубликаты если они есть
        summary_DOUBLES_HIDE = config.SOPDS_DOUBLES_HIDE and (searchtype != "d")
        start = (
            op.d1_first_pos
            if ((op.d1_first_pos == 0) or (not summary_DOUBLES_HIDE))
            else op.d1_first_pos - 1
        )
        finish = op.d1_last_pos

        for row in books[start : finish + 1]:
            p = {
                "doubles": 0,
                "lang_code": row.lang_code,
                "filename": row.filename,
                "path": row.path,
                "registerdate": row.registerdate,
                "id": row.id,  # ty: ignore [unresolved-attribute]
                "annotation": strip_tags(row.annotation),
                "docdate": row.docdate,
                "format": row.format,
                "title": row.title,
                "filesize": row.filesize // 1000,
                "authors": row.authors.values(),
                "genres": row.genres.values(),
                "series": row.series.values(),
                "ser_no": row.bseries_set.values("ser_no"),  # ty: ignore [unresolved-attribute]
            }
            if summary_DOUBLES_HIDE:
                title: str = p["title"]
                authors_set: set[int] = {a["id"] for a in p["authors"]}
                if (
                    title.upper() == prev_title.upper()
                    and authors_set == prev_authors_set
                ):
                    items[-1]["doubles"] += 1
                else:
                    items.append(p)
                prev_title = title
                prev_authors_set = authors_set
            else:
                items.append(p)

        # "вытягиваем" дубликаты книг со следующей страницы и удаляем первый элемент который с предыдущей страницы и "вытягивал" дубликаты с текущей
        if summary_DOUBLES_HIDE:
            double_flag = True
            while ((finish + 1) < books_count) and double_flag:
                finish += 1
                if (
                    books[finish].title.upper() == prev_title.upper()
                    and {a["id"] for a in books[finish].authors.values()}
                    == prev_authors_set
                ):
                    items[-1]["doubles"] += 1
                else:
                    double_flag = False

            if op.d1_first_pos != 0:
                items.pop(0)

        return {
            "books": items,
            "searchterms": searchterms,
            "searchterms0": searchterms0,
            "searchtype": searchtype,
            "paginator": op.get_data_dict(),
        }

    def get_link_kwargs(self, obj):
        kwargs = {"searchtype": obj["searchtype"], "searchterms": obj["searchterms"]}
        if obj.get("searchterms0") is not None:
            kwargs["searchterms0"] = obj["searchterms0"]
        return kwargs

    def link(self, obj):
        return reverse("opds_catalog:searchbooks", kwargs=self.get_link_kwargs(obj))

    def feed_extra_kwargs(self, obj):
        kwargs = self.get_link_kwargs(obj)
        if obj["paginator"]["has_previous"]:
            kwargs["page"] = obj["paginator"]["previous_page_number"]
            prev_url = reverse("opds_catalog:searchbooks", kwargs=kwargs)
        else:
            prev_url = None

        if obj["paginator"]["has_next"]:
            kwargs["page"] = obj["paginator"]["next_page_number"]
            next_url = reverse("opds_catalog:searchbooks", kwargs=kwargs)
        else:
            next_url = None
        return {
            "searchTerm_url": "%s%s"
            % (reverse("opds_catalog:opensearch"), "{searchTerms}/"),
            "start_url": reverse("opds_catalog:main"),
            "description_mime_type": "text/html",
            "prev_url": prev_url,
            "next_url": next_url,
        }

    def items(self, obj):
        return obj["books"]

    def item_title(self, item):
        return item["title"]

    def item_guid(self, item):
        return "b:%s" % (item["id"])

    def item_link(self, item):
        return reverse(
            "opds_catalog:download", kwargs={"book_id": item["id"], "zip_flag": 0}
        )

    def item_updateddate(self, item):
        return item["registerdate"]

    def item_enclosures(self, item):
        mime = mime_detector.fmt(item["format"])
        enclosure = [
            opdsEnclosure(
                reverse(
                    "opds_catalog:download",
                    kwargs={"book_id": item["id"], "zip_flag": 0},
                ),
                mime,
                "http://opds-spec.org/acquisition/open-access",
            ),
        ]
        if item["format"] not in settings.NOZIP_FORMATS:
            mimezip = Mimetype.FB2_ZIP if mime == Mimetype.FB2 else "%s+zip" % mime
            enclosure += [
                opdsEnclosure(
                    reverse(
                        "opds_catalog:download",
                        kwargs={"book_id": item["id"], "zip_flag": 1},
                    ),
                    mimezip,
                    "http://opds-spec.org/acquisition/open-access",
                )
            ]
        enclosure += [
            opdsEnclosure(
                reverse("opds_catalog:cover", kwargs={"book_id": item["id"]}),
                "image/jpeg",
                "http://opds-spec.org/image",
            ),
            opdsEnclosure(
                reverse("opds_catalog:thumb", kwargs={"book_id": item["id"]}),
                "image/jpeg",
                "http://opds-spec.org/thumbnail",
            ),
        ]
        if (config.SOPDS_FB2TOEPUB != "") and (item["format"] == "fb2"):
            enclosure += [
                opdsEnclosure(
                    reverse(
                        "opds_catalog:convert",
                        kwargs={"book_id": item["id"], "convert_type": "epub"},
                    ),
                    Mimetype.EPUB,
                    "http://opds-spec.org/acquisition/open-access",
                )
            ]
        if (config.SOPDS_FB2TOMOBI != "") and (item["format"] == "fb2"):
            enclosure += [
                opdsEnclosure(
                    reverse(
                        "opds_catalog:convert",
                        kwargs={"book_id": item["id"], "convert_type": "mobi"},
                    ),
                    Mimetype.MOBI,
                    "http://opds-spec.org/acquisition/open-access",
                )
            ]

        return enclosure

    def item_extra_kwargs(self, item):
        return {
            "authors": item["authors"],
            "genres": item["genres"],
            "doubles": item["id"] if item["doubles"] > 0 else None,
        }

    def item_description(self, item):
        s = "<b> Book name: </b>%(title)s<br/>"
        if item["authors"]:
            s += _("<b>Authors: </b>%(authors)s<br/>")
        if item["genres"]:
            s += _("<b>Genres: </b>%(genres)s<br/>")
        if item["series"]:
            s += _("<b>Series: </b>%(series)s<br/>")
        if item["ser_no"]:
            s += _("<b>No in Series: </b>%(ser_no)s<br/>")
        s += _(
            "<b>File: </b>%(filename)s<br/><b>File size: </b>%(filesize)s<br/><b>Changes date: </b>%(docdate)s<br/>"
        )
        if item["doubles"]:
            s += _("<b>Doubles count: </b>%(doubles)s<br/>")
        s += "<p class='book'>%(annotation)s</p>"
        return s % {
            "title": item["title"],
            "filename": item["filename"],
            "filesize": item["filesize"],
            "docdate": item["docdate"],
            "doubles": item["doubles"],
            "annotation": item["annotation"],
            "authors": ", ".join(a["full_name"] for a in item["authors"]),
            "genres": ", ".join(g["subsection"] for g in item["genres"]),
            "series": ", ".join(s["ser"] for s in item["series"]),
            "ser_no": ", ".join(str(s["ser_no"]) for s in item["ser_no"]),
        }


class SelectSeriesFeed(AuthFeed):
    """Фид для серий."""

    feed_type = opdsFeed
    subtitle = settings.SUBTITLE

    def title(self, obj):
        return "%s | %s" % (settings.TITLE, _("Series by authors select"))

    def get_object(self, request, searchtype, searchterms):
        try:
            author_id = int(searchterms)
        except:
            author_id = 0
        return author_id

    def link(self, obj):
        return reverse(
            "opds_catalog:searchbooks", kwargs={"searchtype": "as", "searchterms": obj}
        )

    def items(self, obj):
        return [
            {
                "id": 1,
                "title": _("Books by series"),
                "author": obj,
                "descr": _("Books by author and series"),
            },
            {
                "id": 2,
                "title": _("Books outside series"),
                "author": obj,
                "descr": _("Books by author outside series"),
            },
            {
                "id": 3,
                "title": _("Books by alphabet"),
                "author": obj,
                "descr": _("Books by author alphabetical order"),
            },
        ]

    def item_link(self, item):
        if item["id"] == 1:
            return reverse(
                "opds_catalog:searchseries",
                kwargs={"searchtype": "a", "searchterms": item["author"]},
            )
        elif item["id"] == 2:
            return reverse(
                "opds_catalog:searchbooks",
                kwargs={
                    "searchtype": "as",
                    "searchterms": item["author"],
                    "searchterms0": 0,
                },
            )
        elif item["id"] == 3:
            return reverse(
                "opds_catalog:searchbooks",
                kwargs={"searchtype": "a", "searchterms": item["author"]},
            )

    def item_title(self, item):
        return item["title"]

    def item_description(self, item):
        return item["descr"]

    def item_guid(self, item):
        return "as:%s" % item["id"]

    def item_updateddate(self):
        return timezone.now()

    def item_enclosures(self, item):
        return (
            opdsEnclosure(
                self.item_link(item),
                "application/atom+xml;profile=opds-catalog;kind=navigation",
                "subsection",
            ),
        )


class SearchAuthorsFeed(AuthFeed):
    """Фид поиска по авторам."""

    feed_type = opdsFeed
    subtitle = settings.SUBTITLE

    def title(self, obj):
        return "%s | %s" % (settings.TITLE, _("Authors found"))

    def get_object(self, request, searchterms, searchtype, page=1):
        if not isinstance(page, int):
            page = int(page)
        page_num = page if page > 0 else 1

        if searchtype == "m":
            authors = Author.objects.filter(
                search_full_name__contains=searchterms.upper()
            ).order_by("search_full_name")
        elif searchtype == "b":
            authors = Author.objects.filter(
                search_full_name__startswith=searchterms.upper()
            ).order_by("search_full_name")
        elif searchtype == "e":
            authors = Author.objects.filter(
                search_full_name=searchterms.upper()
            ).order_by("search_full_name")

        # Создаем результирующее множество
        authors_count = authors.count()
        op = OPDS_Paginator(authors_count, 0, page_num, config.SOPDS_MAXITEMS)
        items = []

        for row in authors[op.d1_first_pos : op.d1_last_pos + 1]:
            p = {
                "id": row.id,  # ty: ignore [unresolved-attribute]
                "full_name": row.full_name,
                "lang_code": row.lang_code,
                "book_count": Book.objects.filter(authors=row).count(),
            }
            items.append(p)

        return {
            "authors": items,
            "searchterms": searchterms,
            "searchtype": searchtype,
            "paginator": op.get_data_dict(),
        }

    def link(self, obj):
        return reverse(
            "opds_catalog:searchauthors",
            kwargs={"searchtype": obj["searchtype"], "searchterms": obj["searchterms"]},
        )

    def feed_extra_kwargs(self, obj):
        if obj["paginator"]["has_previous"]:
            prev_url = reverse(
                "opds_catalog:searchauthors",
                kwargs={
                    "searchtype": obj["searchtype"],
                    "searchterms": obj["searchterms"],
                    "page": (obj["paginator"]["previous_page_number"]),
                },
            )
        else:
            prev_url = None

        if obj["paginator"]["has_next"]:
            next_url = reverse(
                "opds_catalog:searchauthors",
                kwargs={
                    "searchtype": obj["searchtype"],
                    "searchterms": obj["searchterms"],
                    "page": (obj["paginator"]["next_page_number"]),
                },
            )
        else:
            next_url = None
        return {
            "searchTerm_url": "%s%s"
            % (reverse("opds_catalog:opensearch"), "{searchTerms}/"),
            "start_url": reverse("opds_catalog:main"),
            "description_mime_type": "text",
            "prev_url": prev_url,
            "next_url": next_url,
        }

    def items(self, obj):
        return obj["authors"]

    def item_title(self, item):
        return item["full_name"]

    def item_description(self, item):
        return _("Books count: %s") % (Book.objects.filter(authors=item["id"]).count())

    def item_guid(self, item):
        return "a:%s" % (item["id"])

    def item_link(self, item):
        return reverse(
            "opds_catalog:searchbooks",
            kwargs={"searchtype": "as", "searchterms": item["id"]},
        )

    def item_enclosures(self, item):
        return (
            opdsEnclosure(
                self.item_link(item),
                "application/atom+xml;profile=opds-catalog;kind=navigation",
                "subsection",
            ),
        )


class SearchSeriesFeed(AuthFeed, PaginatorMixin):
    feed_type = opdsFeed
    subtitle = settings.SUBTITLE

    def title(self, obj):
        return "%s | %s" % (settings.TITLE, _("Series found"))

    def get_object(self, request, searchterms, searchtype, page=1):
        self.author_id = None
        if not isinstance(page, int):
            page = int(page)
        page_num = page if page > 0 else 1

        if searchtype == "m":
            series = Series.objects.filter(search_ser__contains=searchterms.upper())
        elif searchtype == "b":
            series = Series.objects.filter(search_ser__startswith=searchterms.upper())
        elif searchtype == "e":
            series = Series.objects.filter(search_ser=searchterms.upper())
        elif searchtype == "a":
            try:
                self.author_id = int(searchterms)
            except:
                self.author_id = None
            series = Series.objects.filter(book__authors=self.author_id)

        series = (
            series.annotate(count_book=Count("book")).distinct().order_by("search_ser")
        )

        # Создаем результирующее множество
        series_count = series.count()
        op = OPDS_Paginator(series_count, 0, page_num, config.SOPDS_MAXITEMS)
        items = []

        for row in series[op.d1_first_pos : op.d1_last_pos + 1]:
            p = {
                "id": row.id,  # ty: ignore [unresolved-attribute]
                "ser": row.ser,
                "lang_code": row.lang_code,
                "book_count": row.count_book,  # ty: ignore [unresolved-attribute]
            }
            items.append(p)

        return {
            "series": items,
            "searchterms": searchterms,
            "searchtype": searchtype,
            "paginator": op.get_data_dict(),
        }

    def link(self, obj):
        return reverse(
            "opds_catalog:searchseries",
            kwargs={"searchtype": obj["searchtype"], "searchterms": obj["searchterms"]},
        )

    def feed_extra_kwargs(self, obj):
        prev_url, next_url = self.get_prev_next_urls("opds_catalog:searchseries", obj)
        return {
            "searchTerm_url": "%s%s"
            % (reverse("opds_catalog:opensearch"), "{searchTerms}/"),
            "start_url": reverse("opds_catalog:main"),
            "description_mime_type": "text",
            "prev_url": prev_url,
            "next_url": next_url,
        }

    def items(self, obj):
        return obj["series"]

    def item_title(self, item):
        return "%s" % (item["ser"])

    def item_description(self, item):
        return _("Books count: %s") % item["book_count"]

    def item_guid(self, item):
        return "a:%s" % item["id"]

    def item_link(self, item):
        if self.author_id:
            kwargs = {
                "searchtype": "as",
                "searchterms": self.author_id,
                "searchterms0": item["id"],
            }
        else:
            kwargs = {"searchtype": "s", "searchterms": item["id"]}

        return reverse("opds_catalog:searchbooks", kwargs=kwargs)

    def item_enclosures(self, item):
        return (
            opdsEnclosure(
                self.item_link(item),
                OPDSLinkType.Navigation,
                "subsection",
            ),
        )


class LangFeed(AuthFeed):
    feed_type = opdsFeed
    subtitle = settings.SUBTITLE

    def link(self, obj):
        return self.request.path

    def title(self, obj):
        return f"{settings.TITLE} | {_('Select language')}"

    def items(self):
        # TODO: переделать, используя словарь lang_codes
        langitems = [
            {"id": 1, "title": _("Cyrillic")},
            {"id": 2, "title": _("Latin")},
            {"id": 3, "title": _("Digits")},
            {"id": 9, "title": _("Other symbols")},
            {"id": 0, "title": _("Show all")},
        ]
        return langitems

    def item_link(self, item):
        return self.request.path + str(item["id"]) + "/"

    def item_title(self, item):
        return item["title"]

    def item_description(self, item):
        return None

    def item_guid(self, item):
        return "l:%s" % item["id"]

    def item_updateddate(self):
        return timezone.now()

    def item_enclosures(self, item):
        return (
            opdsEnclosure(
                self.item_link(item),
                OPDSLinkType.Navigation,
                "subsection",
            ),
        )


class BooksFeed(AuthFeed):
    feed_type = opdsFeed
    subtitle = settings.SUBTITLE

    def link(self, obj):
        return self.request.path

    def title(self, obj):
        return f"{settings.TITLE} | {_('Select books by substring')}"

    def get_object(self, request, lang_code=0, chars=None):
        self.lang_code = int(lang_code)
        if chars is None:
            chars = ""
        return (len(chars) + 1, chars.upper())

    def items(self, obj):
        length, chars = obj
        if self.lang_code:
            sql = """select %(length)s as l, substring(search_title,1,%(length)s) as id, count(*) as cnt 
                   from opds_catalog_book 
                   where lang_code=%(lang_code)s and search_title like '%(chars)s%%%%'
                   group by substring(search_title,1,%(length)s)
                   order by id""" % {
                "length": length,
                "lang_code": self.lang_code,
                "chars": chars,
            }
        else:
            sql = """select %(length)s as l, substring(search_title,1,%(length)s) as id, count(*) as cnt 
                   from opds_catalog_book 
                   where search_title like '%(chars)s%%%%'
                   group by substring(search_title,1,%(length)s)
                   order by id""" % {"length": length, "chars": chars}

        dataset = Book.objects.raw(sql)
        return dataset

    def item_title(self, item):
        return f"{item.id}"

    def item_description(self, item):
        return _("Found: %s books") % item.cnt

    def item_link(self, item):
        title_full = len(item.id) < item.l
        if item.cnt >= config.SOPDS_SPLITITEMS and not title_full:
            return reverse(
                "opds_catalog:chars_books",
                kwargs={"lang_code": self.lang_code, "chars": item.id},
            )
        else:
            return reverse(
                "opds_catalog:searchbooks",
                kwargs={
                    "searchtype": "b" if not title_full else "e",
                    "searchterms": item.id,
                },
            )

    def item_enclosures(self, item):
        return (
            opdsEnclosure(
                self.item_link(item),
                OPDSLinkType.Navigation,
                "subsection",
            ),
        )


class AuthorsFeed(AuthFeed):
    feed_type = opdsFeed
    subtitle = settings.SUBTITLE

    def link(self, obj):
        return self.request.path

    def title(self, obj):
        return f"{settings.TITLE} | {_('Select authors by substring')}"

    def get_object(self, request, lang_code=0, chars=None):
        self.lang_code = int(lang_code)
        if chars is None:
            chars = ""
        return (len(chars) + 1, chars.upper())

    def items(self, obj):
        length, chars = obj
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
        if self.lang_code:
            query = query.filter(lang_code=self.lang_code)

        return query

    def item_title(self, item):
        return "%s" % item["sid"]

    def item_description(self, item):
        return _("Found: %s authors") % item["cnt"]

    def item_link(self, item):
        last_name_full = len(item["sid"]) < item["l"]
        if (item["cnt"] >= config.SOPDS_SPLITITEMS) and not last_name_full:
            return reverse(
                "opds_catalog:chars_authors",
                kwargs={"lang_code": self.lang_code, "chars": item["sid"]},
            )
        else:
            return reverse(
                "opds_catalog:searchauthors",
                kwargs={
                    "searchtype": "b" if not last_name_full else "e",
                    "searchterms": item["sid"],
                },
            )

    def item_enclosures(self, item):
        return (
            opdsEnclosure(
                self.item_link(item),
                "application/atom+xml;profile=opds-catalog;kind=navigation",
                "subsection",
            ),
        )


class SeriesFeed(AuthFeed):
    feed_type = opdsFeed
    subtitle = settings.SUBTITLE

    def link(self, obj):
        return self.request.path

    def title(self, obj):
        return f"{settings.TITLE} | {_('Select series by substring')}"

    def get_object(self, request, lang_code=0, chars=None):
        self.lang_code = int(lang_code)
        if chars is None:
            chars = ""
        return (len(chars) + 1, chars.upper())

    def items(self, obj):
        length, chars = obj
        if self.lang_code:
            sql = """select %(length)s as l, substring(search_ser,1,%(length)s) as id, count(*) as cnt 
                   from opds_catalog_series 
                   where lang_code=%(lang_code)s and search_ser like '%(chars)s%%%%'
                   group by substring(search_ser,1,%(length)s) 
                   order by id""" % {
                "length": length,
                "lang_code": self.lang_code,
                "chars": chars,
            }
        else:
            sql = """select %(length)s as l, substring(search_ser,1,%(length)s) as id, count(*) as cnt 
                   from opds_catalog_series 
                   where search_ser like '%(chars)s%%%%'
                   group by substring(search_ser,1,%(length)s) 
                   order by id""" % {"length": length, "chars": chars}

        dataset = Series.objects.raw(sql)
        return dataset

    def item_title(self, item):
        return "%s" % item.id

    def item_description(self, item):
        return _("Found: %s series") % item.cnt

    def item_link(self, item):
        series_full = len(item.id) < item.l
        if item.cnt >= config.SOPDS_SPLITITEMS and not series_full:
            return reverse(
                "opds_catalog:chars_series",
                kwargs={"lang_code": self.lang_code, "chars": item.id},
            )
        else:
            return reverse(
                "opds_catalog:searchseries",
                kwargs={
                    "searchtype": "b" if not series_full else "e",
                    "searchterms": item.id,
                },
            )

    def item_enclosures(self, item):
        return (
            opdsEnclosure(
                self.item_link(item),
                "application/atom+xml;profile=opds-catalog;kind=navigation",
                "subsection",
            ),
        )


class GenresFeed(AuthFeed):
    feed_type = opdsFeed
    subtitle = settings.SUBTITLE
    item_updateddate = datetime.datetime.now()

    def link(self, obj):
        return self.request.path

    def title(self, obj):
        return "%s | %s" % (
            settings.TITLE,
            _("Select genres (%s)") % (_("section") if obj == 0 else _("subsection")),
        )

    def get_object(self, request, section: int = 0):
        if not isinstance(section, int):
            self.section_id = int(section)
        else:
            self.section_id = section
        return self.section_id

    def items(self, obj):
        section_id = obj
        if section_id == 0:
            dataset = (
                Genre.objects.values("section")
                .annotate(section_id=Min("id"), num_book=Count("book"))
                .filter(num_book__gt=0)
                .order_by("section")
            )
        else:
            section = Genre.objects.get(id=section_id).section
            dataset = (
                Genre.objects.filter(section=section)
                .annotate(num_book=Count("book"))
                .filter(num_book__gt=0)
                .values()
                .order_by("subsection")
            )
        return dataset

    def item_title(self, item):
        return "%s" % (item["section"] if self.section_id == 0 else item["subsection"])

    def item_description(self, item):
        return _("Found: %s books") % item["num_book"]

    def item_link(self, item):
        if self.section_id == 0:
            return reverse(
                "opds_catalog:genres", kwargs={"section": item["section_id"]}
            )
        else:
            return reverse(
                "opds_catalog:searchbooks",
                kwargs={"searchtype": "g", "searchterms": item["id"]},
            )

    def item_enclosures(self, item):
        return (
            opdsEnclosure(
                self.item_link(item),
                OPDSLinkType.Navigation,
                "subsection",
            ),
        )
