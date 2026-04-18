"""Описание OPDS фидов.

Реализация схемы OPDS каталога версии 1.2.
http://spec.opds.io/opds-1.2.html
"""

from __future__ import annotations

from opds_catalog.services import (
    book_services,
    bookshelf_services,
    catalog_services,
    counter_services,
    genre_services,
    series_services,
    authors_services,
)

from dataclasses import dataclass
from typing import Any

from constance import config
from django.contrib.syndication.views import Feed

from django.http import HttpRequest
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.feedgenerator import Atom1Feed, Enclosure, rfc3339_date
from django.utils.translation import gettext as _

from book_tools.format.mimetype import Mimetype
from opds_catalog import settings

from opds_catalog.opds_paginator import Paginator as OPDS_Paginator

from opds_catalog.services.book_services import OPDSSearchType
from .decorators import sopds_auth_validate


@dataclass
class OPDSLinkType:
    """Типы OPDS ссылок."""

    Navigation = "application/atom+xml;profile=opds-catalog;kind=navigation"
    Acquisition = "application/atom+xml;profile=opds-catalog;kind=acquisition"


class opdsEnclosure(Enclosure):
    """Расширение стандартного класса Enclosure для OPDS."""

    def __init__(self, url: str, mime_type: str, rel: str):
        """Дополнительно сохраняет внутри объекта  параметр rel."""
        self.rel = rel
        super(opdsEnclosure, self).__init__(url, 0, mime_type)


class opdsFeed(Atom1Feed):
    """Класс генерации фида opds."""

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
        handler.characters("\n")

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
        # Base feed items
        handler.addQuickElement("id", self.feed["id"])
        handler.characters("\n")
        handler.addQuickElement("icon", settings.ICON)
        handler.characters("\n")
        handler.characters("\n")
        handler.addQuickElement("title", self.feed["title"])
        handler.characters("\n")
        if self.feed.get("subtitle") is not None:
            handler.addQuickElement("subtitle", self.feed["subtitle"])
        handler.characters("\n")
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
        handler.characters("\n")
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


class SOPDSBaseFeed(Feed):
    """Расширение стандартного класса фидов Django для создания OPDS фидов.

    Отличия от базового класса:
    Добавлена работа с авторизацией.
    Введены методы построения Enclosure для навигационных и загрузочных фидов.
    Добавлен базовый метод feed_extra_kwargs.
    """

    feed_type = opdsFeed
    subtitle = settings.SUBTITLE
    item_updateddate = timezone.now()

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

    def catalog_pages_parameters(
        self, paginator: dict, id
    ) -> tuple[str | None, str | None]:
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
        kwargs = {
            "searchtype": obj["searchtype"],
            "searchterms": obj["searchterms"],
        }
        if obj.get("searchterms0") is not None:
            kwargs["searchterms0"] = obj["searchterms0"]

        if obj["paginator"]["has_previous"]:
            kwargs["page"] = obj["paginator"]["previous_page_number"]
            prev_url = reverse(viewname, kwargs=kwargs)
        else:
            prev_url = None

        if obj["paginator"]["has_next"]:
            kwargs["page"] = obj["paginator"]["next_page_number"]
            next_url = reverse(viewname, kwargs=kwargs)
        else:
            next_url = None
        return prev_url, next_url

    def navigation_item_enclosures(self, item):
        """Приложение к элементу навигационного фида.

        Содержит навигационную ссылку для получения детализации элемента.

        :param item: элемент навигационного фида.
        :type item: Any
        """
        return (
            opdsEnclosure(
                self.item_link(item),
                OPDSLinkType.Navigation,
                "subsection",
            ),
        )

    def item_title(self, item):
        """Заголовок элемента каталога."""
        return item["title"]

    def book_enclosure(self, book) -> list[opdsEnclosure]:
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

    def item_enclosures(self, item):
        return self.navigation_item_enclosures(item)


class MainFeed(SOPDSBaseFeed):
    """Корневой фид."""

    title: str = settings.TITLE

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
                    "catalogs": counter_services.get_catalogs_count(),
                    "books": counter_services.get_books_count(),
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
                "counters": {"authors": counter_services.get_authors_count()},
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
                "counters": {"books": counter_services.get_books_count()},
            },
            {
                "id": 4,
                "title": _("By genres"),
                "link": "opds_catalog:genres",
                "descr": _("Genres: %(genres)s."),
                "counters": {"genres": counter_services.get_genres_count()},
            },
        ]
        series_count = counter_services.get_series_count()

        if series_count > 0:
            mainitems.append(
                {
                    "id": 5,
                    "title": _("By series"),
                    "link": (
                        "opds_catalog:lang_series"
                        if config.SOPDS_ALPHABET_MENU
                        else "opds_catalog:nolang_series"
                    ),
                    "descr": _("Series: %(series)s."),
                    "counters": {"series": counter_services.get_series_count()},
                },
            )
        # TODO: Сюда мы можем попасть либо если выключена авторизация либо если
        # авторизация включена и пользователь авторизован.
        if config.SOPDS_AUTH and self.request.user.is_authenticated:
            mainitems.append(
                {  # ty: ignore
                    "id": 6,
                    "title": _("%(username)s Book shelf")
                    % ({"username": self.request.user.username}),  # ty: ignore[unresolved-attribute]
                    "link": "opds_catalog:bookshelf",
                    "descr": _("%(username)s books readed: %(bookshelf)s."),
                    "counters": {
                        "bookshelf": bookshelf_services.get_bookshelf_books_count(
                            user=self.request.user  # ty: ignore [invalid-argument-type]
                        ),
                        "username": self.request.user.username,  # ty: ignore [unresolved-attribute]
                    },
                },
            )

        return mainitems

    def item_link(self, item):
        """Ссылка на элемент фида."""
        return reverse(item["link"])

    def item_description(self, item):
        """Описание элемента фида."""
        return item["descr"] % item["counters"]

    def item_guid(self, item):
        """Уникальный идентификатор элемента фида."""
        return "m:%s" % item["id"]

    def item_extra_kwargs(self, item):
        """Дополнительные атрибуты элемента фида."""
        disable_item_links = list(item["counters"].values())[0] == 0
        return {"disable_item_links": disable_item_links}


class CatalogsFeed(SOPDSBaseFeed):
    """Навигационный фид каталогов."""

    def get_object(self, request, cat_id: int | None = None, page: int = 1):
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
            catalog_services.get_by_id(cat_id)
            if cat_id is not None
            else catalog_services.get_root()
        )
        items, pager_data = catalog_services.paginated_catalog_content(
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
        prev_url, next_url = self.catalog_pages_parameters(paginator, cat.id)
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

    def item_guid(self, item) -> str:
        """Уникальный идентификатор элемента фида."""
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
            return self.book_enclosure(item)

    def item_description(self, item):
        """Описание элемента."""
        if item["is_catalog"]:
            return f"Catalog: {item['title']}"
        else:
            return book_services.book_description(item)

    def item_updateddate(self, item):
        """Дата обновления элемента фида."""
        if item["is_catalog"]:
            return timezone.now()
        else:
            return item["registerdate"]


def OpenSearch(request):
    """Выводим шаблон поиска."""
    return render(request, "opensearch.html")


class SearchTypesFeed(SOPDSBaseFeed):
    """Навигационный фид типов поиска книг."""

    def get_object(self, request, searchterms=""):  # ty:ignore [invalid-method-override]
        """Получение объекта фида."""
        return searchterms.replace("+", " ")

    def link(self, obj):
        return "%s%s" % (reverse("opds_catalog:opensearch"), "{searchTerms}/")

    def items(self, obj):
        """Содержимое фида."""
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

    def item_description(self, item):
        return item["descr"]

    def item_guid(self, item):
        return "st:%s" % item["id"]


class SearchBooksFeed(SOPDSBaseFeed):
    """Фид поиска книг."""

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

        if searchtype == OPDSSearchType.ByAuthorAndSeries and searchterms0 is not None:
            st1 = str(searchterms0)
        else:
            st1 = None

        books = book_services.search_book(searchtype, st, st1, request.user)

        items, op = book_services.paginated_book_content(
            books, page_num, searchtype != OPDSSearchType.Doubles
        )

        return {
            "books": items,
            "searchterms": searchterms,
            "searchterms0": searchterms0,
            "searchtype": searchtype,
            "paginator": op.get_data_dict(),
        }

    def get_link_kwargs(self, obj):
        """Дополнительные праметры ссылки."""
        kwargs = {"searchtype": obj["searchtype"], "searchterms": obj["searchterms"]}
        if obj.get("searchterms0") is not None:
            kwargs["searchterms0"] = obj["searchterms0"]
        return kwargs

    def link(self, obj):
        """Ссылка на поисковую страницу."""
        return reverse("opds_catalog:searchbooks", kwargs=self.get_link_kwargs(obj))

    def feed_extra_kwargs(self, obj):
        kwargs = self.get_link_kwargs(obj)
        prev_url, next_url = self.get_prev_next_urls("opds_catalog:searchbooks", obj)
        return {
            "searchTerm_url": "%s%s"
            % (reverse("opds_catalog:opensearch"), "{searchTerms}/"),
            "start_url": reverse("opds_catalog:main"),
            "description_mime_type": "text/html",
            "prev_url": prev_url,
            "next_url": next_url,
        }

    def items(self, obj):
        """Содержимое фида."""
        return obj["books"]

    def item_guid(self, item):
        """Уникальный идентификатор элемента фида."""
        return "b:%s" % (item["id"])

    def item_link(self, item):
        """Ссылка на элемент фида."""
        return reverse(
            "opds_catalog:download", kwargs={"book_id": item["id"], "zip_flag": 0}
        )

    def item_updateddate(self, item):
        """Дата обновления элемента фида."""
        return item["registerdate"]

    def item_enclosures(self, item):
        """Вложения для элемента фида."""
        return self.book_enclosure(item)

    def item_extra_kwargs(self, item):
        """Дополнительные праметры элемента фида."""
        return {
            "authors": item["authors"],
            "genres": item["genres"],
            "doubles": item["id"] if item["doubles"] > 0 else None,
        }

    def item_description(self, item):
        """Описание элемента фида."""
        return book_services.book_description(item)


class SelectSeriesFeed(SOPDSBaseFeed):
    """Навигационный фид для серий."""

    def title(self, obj):
        return "%s | %s" % (settings.TITLE, _("Series by authors select"))

    def get_object(self, request, searchtype, searchterms):
        return self._to_int(searchterms)

    def link(self, obj):
        """Ссылка на фид."""
        return reverse(
            "opds_catalog:searchbooks", kwargs={"searchtype": "as", "searchterms": obj}
        )

    def items(self, obj):
        """Перечень элементов фида."""
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
        """Ссылка на просмотр элемента."""
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

    def item_description(self, item):
        """Описание элемента фида."""
        return item["descr"]

    def item_guid(self, item):
        """Уникальный идентификатор элемента."""
        return "as:%s" % item["id"]


class SearchAuthorsFeed(SOPDSBaseFeed):
    """Навигационный фид поиска по авторам."""

    def title(self, obj):
        """Заголовок фида."""
        return "%s | %s" % (settings.TITLE, _("Authors found"))

    def get_object(self, request, searchterms, searchtype, page=1):  # ty:ignore[invalid-method-override]
        """Содержимое фида."""
        if not isinstance(page, int):
            page = int(page)
        page_num = page if page > 0 else 1

        authors = authors_services.search_authors(searchtype, searchterms)

        # Создаем результирующее множество
        authors_count = authors.count()
        op = OPDS_Paginator(authors_count, 0, page_num, config.SOPDS_MAXITEMS)
        items = []

        for row in authors[op.d1_first_pos : op.d1_last_pos + 1]:
            p = {
                "id": row.id,  # ty: ignore [unresolved-attribute]
                "full_name": row.full_name,
                "lang_code": row.lang_code,
                "book_count": book_services.author_books_count(row),
            }
            items.append(p)

        return {
            "authors": items,
            "searchterms": searchterms,
            "searchtype": searchtype,
            "paginator": op.get_data_dict(),
        }

    def link(self, obj):
        """Ссылка на фид."""
        return reverse(
            "opds_catalog:searchauthors",
            kwargs={"searchtype": obj["searchtype"], "searchterms": obj["searchterms"]},
        )

    def feed_extra_kwargs(self, obj):
        """Дополнительные атрибуты фида."""
        prev_url, next_url = self.get_prev_next_urls("opds_catalog:searchauthors", obj)
        return {
            "searchTerm_url": "%s%s"
            % (reverse("opds_catalog:opensearch"), "{searchTerms}/"),
            "start_url": reverse("opds_catalog:main"),
            "description_mime_type": "text",
            "prev_url": prev_url,
            "next_url": next_url,
        }

    def items(self, obj):
        """Список авторов."""
        return obj["authors"]

    def item_title(self, item):
        """Заголовок книги."""
        return item["full_name"]

    def item_description(self, item):
        """Количество нйденных книг."""
        return _("Books count: %s") % (book_services.author_books_count(item["id"]))

    def item_guid(self, item):
        """Уникальный идентификатор книги."""
        return "a:%s" % (item["id"])

    def item_link(self, item):
        """Ссылка для просмотр результата поиска книг."""
        return reverse(
            "opds_catalog:searchbooks",
            kwargs={"searchtype": "as", "searchterms": item["id"]},
        )


class SearchSeriesFeed(SOPDSBaseFeed):
    """Навигационный фид поиска серий книг."""

    def title(self, obj):
        """Заголовок фида."""
        return "%s | %s" % (settings.TITLE, _("Series found"))

    def get_object(self, request, searchterms, searchtype, page=1):  # ty: ignore[invalid-method-override]
        """Получение элементов фида."""
        self.author_id = None
        if not isinstance(page, int):
            page = int(page)
        page_num = page if page > 0 else 1

        if searchtype == OPDSSearchType.ByAuthor:
            self.author_id = self._to_int(searchterms)

        series = series_services.search_series(searchtype, searchterms, self.author_id)

        # Создаем результирующее множество
        series_count = series.count()
        op = OPDS_Paginator(series_count, 0, page_num, config.SOPDS_MAXITEMS)
        items = []

        for row in series[op.d1_first_pos : op.d1_last_pos + 1]:
            p = {
                "id": row.id,
                "ser": row.ser,
                "lang_code": row.lang_code,
                "book_count": row.count_book,
            }
            items.append(p)

        return {
            "series": items,
            "searchterms": searchterms,
            "searchtype": searchtype,
            "paginator": op.get_data_dict(),
        }

    def link(self, obj):
        """Ссылка на фид."""
        return reverse(
            "opds_catalog:searchseries",
            kwargs={"searchtype": obj["searchtype"], "searchterms": obj["searchterms"]},
        )

    def feed_extra_kwargs(self, obj):
        """Дополнительные аргументы фида."""
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
        """Найденные серии."""
        return obj["series"]

    def item_title(self, item):
        """Название серии."""
        return "%s" % (item["ser"])

    def item_description(self, item):
        """Количество книг в серии."""
        return _("Books count: %s") % item["book_count"]

    def item_guid(self, item):
        """Уникальный идентификатор серии."""
        return "a:%s" % item["id"]

    def item_link(self, item):
        """Ссылка на серию."""
        if self.author_id:
            kwargs = {
                "searchtype": "as",
                "searchterms": self.author_id,
                "searchterms0": item["id"],
            }
        else:
            kwargs = {"searchtype": "s", "searchterms": item["id"]}

        return reverse("opds_catalog:searchbooks", kwargs=kwargs)


class LangFeed(SOPDSBaseFeed):
    """Навигационный фид для поиска книг по языку."""

    def link(self, obj):
        """Ссылка на фид."""
        return self.request.path

    def title(self, obj):
        """Заголовок фида."""
        return f"{settings.TITLE} | {_('Select language')}"

    def items(self):
        """Перечень языков."""
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
        """Ссылка на дальнейшую навигацию."""
        return self.request.path + str(item["id"]) + "/"

    def item_description(self, item):
        """Описание элемента."""
        return None

    def item_guid(self, item):
        """Уникальный идентификатор элемента."""
        return "l:%s" % item["id"]


class BooksFeed(SOPDSBaseFeed):
    """Навигационный фид для поиска книг по шаблону названия."""

    def link(self, obj):
        """Ссылка на фид."""
        return self.request.path

    def title(self, obj):
        """Заголовок фида."""
        return f"{settings.TITLE} | {_('Select books by substring')}"

    def get_object(self, request, lang_code=0, chars=None):  # ty: ignore [invalid-method-override]
        """Формирование шаблона названия книги."""
        self.lang_code = int(lang_code)
        if chars is None:
            chars = ""
        return (len(chars) + 1, chars.upper())

    def items(self, obj):
        """Получение содержимого фида."""
        length, chars = obj
        return book_services.find_books_by_template(chars, length, self.lang_code)

    def item_title(self, item):
        """Шаблон названия книги."""
        return f"{item.id}"

    def item_description(self, item):
        """Количество найденных по шаблону книг."""
        return _("Found: %s books") % item.cnt

    def item_link(self, item):
        """Построение ссылок на дальнейшую навигацию."""
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
                    "searchtype": OPDSSearchType.ByStartWith
                    if not title_full
                    else OPDSSearchType.ByExact,
                    "searchterms": item.id,
                },
            )


class AuthorsFeed(SOPDSBaseFeed):
    """Навигационный фид для поиска книг по автору."""

    def link(self, obj):
        """Ссылка на фид."""
        return self.request.path

    def title(self, obj):
        """Заголовок фида."""
        return f"{settings.TITLE} | {_('Select authors by substring')}"

    def get_object(self, request, lang_code=0, chars=None):  # ty: ignore [invalid-method-override]
        """Формирование шаблона для поиска авторов."""
        self.lang_code = int(lang_code)
        if chars is None:
            chars = ""
        # FIXME: вычисление len(chars+1) должно быть в сервисе.
        return (len(chars) + 1, chars.upper())

    def items(self, obj):
        """Запрос авторов, подпадающих под заданный шаблон."""
        length, chars = obj
        return authors_services.find_authors_by_template(chars, length, self.lang_code)

    def item_title(self, item):
        """Начало фамилий авторов."""
        return "%s" % item["sid"]

    def item_description(self, item):
        """Количество найденных авторов."""
        return _("Found: %s authors") % item["cnt"]

    def item_link(self, item):
        """Ссылка для получения списка авторов.

        Если число символов для поиска авторов меньше заданного в настройках,
        то возвращется перечень ссылок для авторов, начинающихся с заданной
        последовательности символов + 1 дополнительный символ.
        Если же число символов более заданного в настройках, то возвращается
        перечень ссылок на авторов.

        :param item: Начало фамилии автора.
        :type item: str | None

        :returns: сссылка на продолжение поиска по авторам.
        :rtype: str
        """
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


class SeriesFeed(SOPDSBaseFeed):
    """Навигационный фид для поиска книг по сериям.

    Фид итеративно отображает начальные символы названия серий и количество серий,
    которые начинаются на эти символы.
    """

    def link(self, obj):
        """Ссылка на фид."""
        return self.request.path

    def title(self, obj):
        """Заголовок фида серий."""
        return f"{settings.TITLE} | {_('Select series by substring')}"

    def get_object(self, request, lang_code=0, chars=None):  # ty: ignore[invalid-method-override]
        """Получение основного объекта фида."""
        self.lang_code = int(lang_code)
        if chars is None:
            chars = ""
        return (len(chars) + 1, chars.upper())

    def items(self, obj):
        """Список серий, отображаемых в фиде."""
        length, chars = obj
        return series_services.get_series(chars, length, self.lang_code)

    def item_title(self, item):
        """Идентификатор серии."""
        return f"{item.id}"

    def item_description(self, item):
        """Количество книг в серии."""
        return _("Found: %s series") % item.cnt

    def item_link(self, item) -> str:
        """Ссылка для получения списка серий.

        Если число символов для поиска серий меньше заданного в настройках,
        то возвращется перечень ссылок для серий, начинающихся с заданной
        последовательности символов + 1 дополнительный символ.
        Если же число символов более заданного в настройках, то возвращается
        перечень ссылок на серии.

        :param item: Начало названия серии.
        :type item: str | None

        :returns: сссылка на продолжение поиска по серии
        :rtype: str
        """
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
                    "searchtype": OPDSSearchType.ByStartWith
                    if not series_full
                    else OPDSSearchType.ByExact,
                    "searchterms": item.id,
                },
            )


class GenresFeed(SOPDSBaseFeed):
    """Навигационный фид для поиска книг по жанру.

    Предоставляет навигацию по жанрам c указанием количества книг для выбранного жанра.
    """

    def link(self, obj):
        """Ссылка на фид."""
        return self.request.path

    def title(self, obj):
        """Заголовок фида."""
        return "%s | %s" % (
            settings.TITLE,
            _("Select genres (%s)") % (_("section") if obj == 0 else _("subsection")),
        )

    def get_object(self, request, section: int = 0):  # ty:ignore [invalid-method-override]
        """Получение данных фида."""
        if not isinstance(section, int):
            self.section_id = int(section)
        else:
            self.section_id = section
        return self.section_id

    def items(self, obj):
        """Предоставляет перечень жанров или поджанров для поиска книг.

        Возвращается только перечень жанров или поджанров, в котором есть книги.
        Если для какого-то из жанров книг в библиотеке не зарегистрировано, то этот жанр
        в результирующий список не попадает.

        :param obj: идентификатор секции.
        :type obj: int

        :returns: Если в идентификатре секции передан 0, то врзвращается перечень всех
        основных жанров книг. В противном случае возвращается перечень поджанров
        выбранного жанра.
        """
        section_id = obj
        if section_id == 0:
            dataset = genre_services.get_genres()
        else:
            dataset = genre_services.get_genre_details(section_id)
        return dataset

    def item_title(self, item):
        """Название жанра или поджанра."""
        return "%s" % (item["section"] if self.section_id == 0 else item["subsection"])

    def item_description(self, item):
        """количество книг для жанра."""
        return _("Found: %s books") % item["num_book"]

    def item_link(self, item):
        """Ссылка на детализацию жанра.

        Эта ссылка ведет на навигационный каталог поиска книг по жанру.
        """
        if self.section_id == 0:
            return reverse(
                "opds_catalog:genres", kwargs={"section": item["section_id"]}
            )
        else:
            return reverse(
                "opds_catalog:searchbooks",
                kwargs={
                    "searchtype": OPDSSearchType.ByGenre,
                    "searchterms": item["id"],
                },
            )
