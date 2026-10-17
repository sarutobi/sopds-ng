"""Сервис сохранения книг с поддержкой кэширования и ленивой загрузки справочников.

Этот сервис инкапсулирует всю логику записи книг в базу данных, обеспечивая
единую точку входа для различных источников данных (INPX, raw_scan).
"""

import logging
import re
from dataclasses import dataclass
from typing import Iterable, Protocol

from opds_catalog.models import (
    SIZE_AUTHOR_NAME,
    SIZE_BOOK_TITLE,
    SIZE_GENRE,
    SIZE_SERIES,
    Author,
    Book,
    Catalog,
    Genre,
    Series,
    bseries,
)
from opds_catalog.services.dto import (
    BookMetadata,
)
from opds_catalog.utils import getlangcode

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FileSpec:
    """Параметры файла-носителя книги, предоставляемые источником."""

    path: str
    filename: str
    rel_path: str
    extension: str
    file_size: int


@dataclass(frozen=True)
class WriteOutcome:
    """Результат сохранения книги; статистика выводится вызывающим кодом."""

    book: Book
    created: bool
    authors_linked: int
    genres_linked: int
    series_linked: int


class SnapshotSource(Protocol):
    """Источник прогревочных строк справочников.

    Позволяет передать результат read-snapshot, выполненного ВНЕ write-транзакции.
    """

    def authors(self) -> Iterable[tuple[str, Author]]: ...
    def genres(self) -> Iterable[tuple[str, Genre]]: ...
    def series(self) -> Iterable[tuple[str, Series]]: ...


class BookWriter:
    """Сервис сохранения книги со связями. Держит состояние сессии скана."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(__name__)
        self._authors: dict[str, Author] = {}
        self._genres: dict[str, Genre] = {}
        self._series: dict[str, Series] = {}
        self._cats: dict[str, Catalog] = {}

    def _normalize_string(self, value: str, type: str) -> str:
        """Единый канон нормализации строк для ключей кэша и БД (SEC-06)."""
        if not value:
            return ""

        normalized = value.strip()

        if type == "author":
            # Решение D-2: Перенос фамилии в начало (если нет запятой)
            if "," not in normalized:
                parts = normalized.rsplit(None, 1)
                if len(parts) > 1:
                    normalized = f"{parts[1]}, {parts[0]}"
        elif type == "genre":
            # Жанры: нижний регистр + strip
            normalized = normalized.lower()
        elif type == "series":
            # Серии: нижний регистр + замена спецсимволов на пробелы + схлопывание пробелов
            normalized = normalized.lower()
            # Заменяем всё, что не буквы/цифры, на пробел
            normalized = re.sub(r"[^a-zа-яё0-9]+", " ", normalized)
            # Схлопываем последовательности пробелов в один
            normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def _cache_key(self, value: str, type: str) -> str:
        """Формирует канонический ключ кэша (design §2.6)."""
        normalized = self._normalize_string(value, type)

        size = {
            "author": SIZE_AUTHOR_NAME,
            "genre": SIZE_GENRE,
            "series": SIZE_SERIES,
        }.get(type, 255)

        return normalized[:size]

    def warmup(self, source: SnapshotSource | None = None) -> None:
        """Прогрев кэша справочников из источника (design §4)."""
        if source is None:
            return

        # Заполнение кэша авторов
        for key, author in source.authors():
            self._authors[self._cache_key(key, "author")] = author

        # Заполнение кэша жанров
        for key, genre in source.genres():
            self._genres[self._cache_key(key, "genre")] = genre

        # Заполнение кэша серий
        for key, series in source.series():
            self._series[self._cache_key(key, "series")] = series

    def _resolve_author(self, full_name: str) -> Author:
        """Резолвер автора: кэш -> БД -> create."""
        key = self._cache_key(full_name, "author")
        if key in self._authors:
            return self._authors[key]

        try:
            author = Author.objects.get(full_name=key)
        except Author.DoesNotExist:
            author = Author.objects.create(
                full_name=full_name[:SIZE_AUTHOR_NAME],
                search_full_name=key,
                lang_code=getlangcode(full_name),
            )

        self._authors[key] = author
        return author

    def _resolve_genre(self, genre_name: str) -> Genre:
        """Резолвер жанра: кэш -> БД -> create."""
        key = self._cache_key(genre_name, "genre")
        if key in self._genres:
            return self._genres[key]

        try:
            genre = Genre.objects.get(genre=key)
        except Genre.DoesNotExist:
            genre = Genre.objects.create(
                genre=key,
                section="Unknown genre",
                subsection=key,
            )

        self._genres[key] = genre
        return genre

    def _resolve_series(self, series_name: str) -> Series:
        """Резолвер серии: кэш -> БД -> create."""
        # Ключ для кэша и поиска в БД всегда нормализован
        key = self._cache_key(series_name, "series")
        if key in self._series:
            return self._series[key]

        try:
            # Поиск по нормализованному ключу в search_ser
            series = Series.objects.get(search_ser=key)
        except Series.DoesNotExist:
            # При создании сохраняем оригинальное имя в ser, а ключ в search_ser
            series = Series.objects.create(
                ser=series_name[:SIZE_SERIES],
                search_ser=key,
                lang_code=getlangcode(series_name),
            )

        self._series[key] = series
        return series

    def exists(self, file: FileSpec) -> bool:
        """Быстрая проверка существования книги по параметрам файла.
        Если книга найдена, обновляет её доступность (avail=2) (SEC-04).
        """
        updated = Book.objects.filter(
            path=file.rel_path, filename=file.filename
        ).update(avail=2)
        return updated > 0

    def save_book(
        self,
        meta: BookMetadata,
        *,
        file: FileSpec,
        catalog: Catalog,
        cat_type: int,
    ) -> WriteOutcome:
        """Сохранение книги и установление связей (design §2.1)."""
        from opds_catalog.utils import p

        # SEC-03: Нормализация данных и защита от DoS/ошибок БД
        # 1. Фолбэк для заголовка (если пуст -> имя файла)
        title = (meta.title or "").strip() or file.filename

        # 2. Принудительное усечение и очистка от символов вне BMP
        norm_title = p(title, SIZE_BOOK_TITLE)
        norm_annotation = p(meta.annotation or "", 10000)
        norm_docdate = p(meta.docdate or "", 32)
        norm_lang = p(meta.lang or "", 16)
        norm_format = p(file.extension or "", 8)

        # Идемпотентность по (path, filename)
        try:
            book = Book.objects.get(path=file.rel_path, filename=file.filename)
            book.avail = 2
            # Обновляем поля, чтобы в БД всегда были нормализованные данные
            book.title = norm_title
            book.annotation = norm_annotation
            book.docdate = norm_docdate
            book.lang = norm_lang
            book.format = norm_format
            book.save()
            # Связи не пересоздаются при нахождении книги
            return WriteOutcome(
                book=book,
                created=False,
                authors_linked=0,
                genres_linked=0,
                series_linked=0,
            )
        except Book.DoesNotExist:
            # Создание новой книги с нормализованными данными
            book = Book.objects.create(
                path=file.rel_path,
                filename=file.filename,
                title=norm_title,
                search_title=norm_title.upper(),
                avail=2,
                catalog=catalog,
                cat_type=cat_type,
                filesize=file.file_size,
                format=norm_format,
                docdate=norm_docdate,
                lang=norm_lang,
                lang_code=getlangcode(norm_title),
                annotation=norm_annotation,
            )

        # Используем единый канон нормализации для авторов
        authors_linked = 0
        for a_meta in meta.authors:
            author = self._resolve_author(a_meta.full_name)
            book.authors.add(author)
            authors_linked += 1

        # Связи с жанрами
        genres_linked = 0
        for g_name in meta.genres:
            genre = self._resolve_genre(g_name)
            book.genres.add(genre)
            genres_linked += 1

        # Связи с сериями
        series_linked = 0
        for s_meta in meta.series:
            series = self._resolve_series(s_meta.name)
            # Используем get_or_create для связи с серией, чтобы сохранить ser_no

            bseries.objects.get_or_create(
                book=book, ser=series, defaults={"ser_no": s_meta.series_no}
            )
            series_linked += 1

        return WriteOutcome(
            book=book,
            created=True,
            authors_linked=authors_linked,
            genres_linked=genres_linked,
            series_linked=series_linked,
        )
