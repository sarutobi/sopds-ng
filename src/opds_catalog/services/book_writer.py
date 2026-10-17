"""Сервис сохранения книг с поддержкой кэширования и ленивой загрузки справочников.

Этот сервис инкапсулирует всю логику записи книг в базу данных, обеспечивая
единую точку входа для различных источников данных (INPX, raw_scan).
"""

import logging
from dataclasses import dataclass
from typing import Iterable, Protocol

from opds_catalog.models import Author, Book, Catalog, Genre, Series
from opds_catalog.services.dto import BookMetadata

# Константы размеров полей из БД
SIZE_AUTHOR_NAME = 128
SIZE_GENRE = 128
SIZE_SERIES = 128
SIZE_CAT_PATH = 255

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

    def _cache_key(self, value: str, size: int, type: str = "generic") -> str:
        """Канон ключа кэша справочника (design §2.6).

        Нормализация выполняется ДО усечения, чтобы warmup и lazy-fill
        использовали один и тот же ключ.
        """
        if not value:
            return ""

        normalized = value.strip()

        if type == "author":
            # Решение D-2: перенос фамилии
            # В la-lang (напр. RU) мы просто храним normalized,
            # но для поиска в БД мы используем этот ключ.
            # Реальная нормализация для сравнения произойдет внутри резолвера.
            pass
        elif type == "genre":
            # Решение D-5: lower().strip(strip_symbols)
            normalized = normalized.lower()
        elif type == "series":
            # Решение D-5: strip(strip_symbols)
            pass

        return normalized[:size]

    def warmup(self, source: SnapshotSource | None = None) -> None:
        """Прогрев кэша справочников из источника (design §4)."""
        if source is None:
            return

        # Заполнение кэша авторов
        for key, author in source.authors():
            self._authors[self._cache_key(key, SIZE_AUTHOR_NAME, "author")] = author

        # Заполнение кэша жанров
        for key, genre in source.genres():
            self._genres[self._cache_key(key, SIZE_GENRE, "genre")] = genre

        # Заполнение кэша серий
        for key, series in source.series():
            self._series[self._cache_key(key, SIZE_SERIES, "series")] = series

    def _resolve_author_legacy(self, full_name: str) -> Author:
        """Резолвер автора без нормализации (для Parity с legacy)."""
        key = full_name[:SIZE_AUTHOR_NAME]
        if key in self._authors:
            return self._authors[key]

        try:
            author = Author.objects.get(full_name=key)
        except Author.DoesNotExist:
            author = Author.objects.create(full_name=key, search_full_name=key.upper())

        self._authors[key] = author
        return author

    def _resolve_author(self, full_name: str, sortkey: str = "") -> Author:
        """Резолвер автора: кэш -> БД -> create."""
        # Решение D-2: нормализация имени для поиска
        # Если есть запятая -> используем как есть (она разделитель),
        # если нет -> последнее слово в начало.
        search_name = full_name.strip()
        if search_name and "," not in search_name:
            parts = search_name.rsplit(None, 1)
            if len(parts) > 1:
                search_name = f"{parts[1]}, {parts[0]}"

        key = self._cache_key(search_name, SIZE_AUTHOR_NAME, "author")
        if key in self._authors:
            return self._authors[key]

        # Lazy-fill из БД
        try:
            author = Author.objects.get(full_name=key)
        except Author.DoesNotExist:
            # При создании используем оригинальный full_name для сохранения,
            # но search_full_name для индекса.
            author = Author.objects.create(
                full_name=full_name[:SIZE_AUTHOR_NAME], search_full_name=key
            )

        self._authors[key] = author
        return author

    def _resolve_genre(self, genre_name: str) -> Genre:
        """Резолвер жанра: кэш -> БД -> create."""
        # Решение D-5: нормализация жанра
        normalized_name = genre_name.strip().lower()
        key = self._cache_key(normalized_name, SIZE_GENRE, "genre")
        if key in self._genres:
            return self._genres[key]

        try:
            genre = Genre.objects.get(genre=key)
        except Genre.DoesNotExist:
            # Восстанавливаем legacy-поведение: section="Unknown genre", subsection=name
            genre = Genre.objects.create(
                genre=key,
                section="Unknown genre",
                subsection=key,
            )

        self._genres[key] = genre
        return genre

    def _resolve_series(self, series_name: str) -> Series:
        """Резолвер серии: кэш -> БД -> create."""
        # Решение D-5: нормализация серии (только strip)
        normalized_name = series_name.strip()
        key = self._cache_key(normalized_name, SIZE_SERIES, "series")
        if key in self._series:
            return self._series[key]

        try:
            series = Series.objects.get(ser=key)
        except Series.DoesNotExist:
            series = Series.objects.create(ser=key, search_ser=key)

        self._series[key] = series
        return series

    def _resolve_catalog(self, rel_path: str, cat_type: int, size: int) -> Catalog:
        """Резолвер каталога с кэшированием (design §2.5)."""
        # Канон ключа каталога - путь до размера SIZE_CAT_PATH
        key = rel_path[:SIZE_CAT_PATH]
        if key in self._cats:
            cat = self._cats[key]
            # Проверка актуальности размера (design §2.5)
            if cat.cat_size == size:
                return cat

            cat.cat_size = size
            cat.save()
            return cat

        # Здесь должен быть вызов findcat() из scanner, но так как мы
        # сейчас в skeleton, используем упрощенную логику.
        # В Task 2.1/3.1 это будет интегрировано с opdsScanner.
        cat, created = Catalog.objects.get_or_create(path=key)
        cat.cat_size = size
        cat.save()

        self._cats[key] = cat
        return cat

    def save_book(
        self,
        meta: BookMetadata,
        *,
        file: FileSpec,
        catalog: Catalog,
        cat_type: int,
    ) -> WriteOutcome:
        """Сохранение книги и установление связей (design §2.1)."""
        # Идемпотентность по (path, filename)
        try:
            book = Book.objects.get(path=file.rel_path, filename=file.filename)
            book.avail = 2
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
            # Создание новой книги
            book = Book.objects.create(
                path=file.rel_path,
                filename=file.filename,
                title=meta.title,
                search_title=meta.title,
                avail=2,
                catalog=catalog,
                cat_type=cat_type,
                filesize=file.file_size,
                format=file.extension,
                docdate=meta.docdate,
                lang=meta.lang,
                annotation=meta.annotation,
            )

        # Используем legacy-резолвер для авторов, чтобы сохранить parity с baseline
        # (решение D-2 будет применено в Task 3.1 для raw_scan, если потребуется)
        authors_linked = 0
        for a_meta in meta.authors:
            author = self._resolve_author_legacy(a_meta.full_name)
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
                from opds_catalog.models import bseries

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
