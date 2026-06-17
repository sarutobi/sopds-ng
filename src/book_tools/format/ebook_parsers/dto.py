# dto.py — Data Transfer Objects для передачи данных между парсерами

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Author:
    """Информация об авторе книги."""

    first_name: str = ""
    last_name: str = ""
    middle_name: Optional[str] = None


@dataclass
class Series:
    """Информация о серии книги."""

    name: str = ""
    series_no: int = 0


@dataclass
class Cover:
    """Информация об обложке."""

    type: str = ""
    image: str = ""


@dataclass
class BookMetadata:
    """Метаданные книги."""

    title: str
    authors: list[Author]
    series: Optional[Series] = None
    genres: list[str] = field(default_factory=list)
    language: str = ""
    description: Optional[str] = None
    publication_date: Optional[date] = None
    docdate: str = ""
    file_size: int = 0
    file_format: str = ""
