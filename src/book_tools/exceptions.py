"""Исключения, возникающие при парсинге электронных книг."""


class EbookParserException(Exception):
    """Базовый класс для исключений при парсинге электронных книг."""

    def __init__(self, error: str | Exception):
        super().__init__(error)


class FB2StructureException(EbookParserException):
    """Исключение при извлечении метаданных из книги в формате fb2."""

    def __init__(self, error: str | Exception):
        super().__init__(f"fb2 verification failed: {error}")


class EpubStructureException(EbookParserException):
    """Исключение при парсинге epub."""

    def __init__(self, message):
        super().__init__(f"ePub verification failed: {message}")


class UnsupportedFormatException(EbookParserException):
    """Неподдерживаемый формат файла для парсинга."""

    def __init__(self, message):
        super().__init__(f"Unsupported format exception: {message}")


class UnsupportedFileType(EbookParserException):
    """MIME-тип распознан, но для него нет зарегистрированного парсера."""

    def __init__(self, mimetype: str, filename: str = ""):
        msg = f"Нет парсера для типа {mimetype}"
        if filename:
            msg += f" ({filename})"
        super().__init__(msg)
