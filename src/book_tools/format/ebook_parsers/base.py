# base.py — абстрактный базовый класс EbookParser

from abc import ABC, abstractmethod
from pathlib import Path

from book_tools.format.parsers.dto import BookMetadata, Cover


class EbookParser(ABC):
    """Абстрактный базовый класс для парсеров электронных книг.

    Все конкретные парсеры должны наследовать этот класс и реализовывать
    его абстрактные методы.
    """

    @abstractmethod
    def parse_metadata(self, file_path: Path) -> BookMetadata:
        """Извлечение метаданных книги.

        Args:
            file_path: Путь к файлу книги.

        Returns:
            BookMetadata: Объект с метаданными книги.

        Raises:
            ParserError: Если файл не может быть прочитан или имеет
                некорректный формат.
        """
        ...

    @abstractmethod
    def extract_cover(self, file_path: Path) -> Cover | None:
        """Извлечение обложки книги.

        Args:
            file_path: Путь к файлу книги.

        Returns:
            bytes | None: Байтовое представление изображения обложки,
                или None, если обложка отсутствует.

        Raises:
            ParserError: Если файл не может быть прочитан или имеет
                некорректный формат.
        """
        ...
