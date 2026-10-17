"""Типы данных для передачи метаданных книг между парсерами и сервисом записи."""

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class AuthorMetadata:
    """Метаданные одного автора."""

    full_name: str
    sortkey: str = ""


@dataclass(frozen=True)
class SeriesMetadata:
    """Метаданные серии книг."""

    name: str
    series_no: int = 0


@dataclass(frozen=True)
class BookMetadata:
    """Унифицированные метаданные книги для сохранения в каталог.

    Используется как DTO (Data Transfer Object) для изоляции логики парсинга
    от логики сохранения в БД.
    """

    title: str
    authors: Sequence[AuthorMetadata] = field(default_factory=list)
    genres: Sequence[str] = field(default_factory=list)
    series: Sequence[SeriesMetadata] = field(default_factory=list)
    annotation: str = ""
    docdate: str = ""
    lang: str = "ru"
