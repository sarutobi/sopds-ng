"""Источники снимков данных для прогрева кэша BookWriter."""

from typing import Iterable

from opds_catalog.models import Author, Genre, Series


class DbSnapshotSource:
    """Источник данных из базы данных для прогрева кэша.

    Этот класс позволяет извлечь текущее состояние справочников одним или
    несколькими пакетными запросами, чтобы избежать N+1 при записи книг.
    """

    def authors(self) -> Iterable[tuple[str, Author]]:
        """Возвращает пары (канонический_ключ, объект_автора)."""
        # Чтобы избежать N+1 в BookWriter.warmup, возвращаем полноценные объекты.
        return ((a.full_name, a) for a in Author.objects.all())

    def genres(self) -> Iterable[tuple[str, Genre]]:
        """Возвращает пары (канонический_ключ, объект_жанра)."""
        return ((g.genre, g) for g in Genre.objects.all())

    def series(self) -> Iterable[tuple[str, Series]]:
        """Возвращает пары (канонический_ключ, объект_серии)."""
        return ((s.ser, s) for s in Series.objects.all())
