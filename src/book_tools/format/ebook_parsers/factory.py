# factory.py — фабрика парсеров

from pathlib import Path

from book_tools.exceptions import UnsupportedFormatError
from book_tools.format.parsers.base import EbookParser


class ParserFactory:
    """Фабрика для получения парсера по расширению файла."""

    _parsers: dict[str, type[EbookParser]] = {}

    @classmethod
    def register(cls, extension: str, parser_cls: type[EbookParser]) -> None:
        """Регистрирует парсер для указанного расширения.

        Args:
            extension: Расширение файла (например, '.fb2').
            parser_cls: Класс парсера, реализующий EbookParser.
        """
        cls._parsers[extension.lower()] = parser_cls

    @classmethod
    def get_parser(cls, file_path: Path) -> EbookParser:
        """Возвращает экземпляр парсера для указанного файла.

        Args:
            file_path: Путь к файлу книги.

        Returns:
            EbookParser: Экземпляр парсера.

        Raises:
            UnsupportedFormatError: Если расширение файла не
                зарегистрировано.
        """
        ext = file_path.suffix.lower()
        if ext not in cls._parsers:
            raise UnsupportedFormatError(f"Неподдерживаемый формат: {ext}")
        return cls._parsers[ext]()
