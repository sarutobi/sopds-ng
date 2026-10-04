"""Исключения, возникающие при парсинге электронных книг."""


class BookToolsError(Exception):
    """Базовый класс для всех исключений модуля book_tools."""


class ParserError(BookToolsError):
    """Ошибка парсинга (в т.ч. поврежденные файлы)."""


class UnsupportedFormatError(ParserError):
    """Неподдерживаемый формат файла для парсинга."""


class FB2StructureException(ParserError):
    """Исключение при извлечении метаданных из книги в формате fb2."""

    def __init__(self, error: str | Exception):
        super().__init__(f"fb2 verification failed: {error}")


class EpubStructureException(ParserError):
    """Исключение при парсинге epub."""

    def __init__(self, message):
        super().__init__(f"ePub verification failed: {message}")


class UnsupportedFileType(UnsupportedFormatError):
    """MIME-тип распознан, но для него нет зарегистрированного парсера."""

    def __init__(self, mimetype: str, filename: str = ""):
        msg = f"Нет парсера для типа {mimetype}"
        if filename:
            msg += f" ({filename})"
        super().__init__(msg)
