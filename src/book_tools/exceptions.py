"""Исключения, возникающие при парсинге электронных книг"""


class EbookParserException(Exception):
    """Базовый класс для исключений при парсинге электронных книг"""

    def __init__(self, error: str | Exception):
        super().__init__(error)


class FB2StructureException(EbookParserException):
    """Исключение при извлечении метаданных из книги в формате fb2"""

    def __init__(self, error: str | Exception):
        super().__init__(f"fb2 verification failed: {error}")


class EpubStructureException(EbookParserException):
    """Исключение при парсинге epub"""

    def __init__(self, message):
        super().__init__(f"ePub verification failed: {message}")
