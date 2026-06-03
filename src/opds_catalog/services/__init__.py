"""Сервисные функции opds_catalog."""

from enum import StrEnum
import zipfile
from io import BytesIO

from constance import config

from book_tools.format.mimetype import Mimetype
from book_tools.format.parsers import FB2, FB2sax


class SearchType(StrEnum):
    """Типы поиска в OPDS-каталоге."""

    # Общие типы поиска (для книг, авторов, серий)
    BY_SUBSTRING = "m"  # Поиск по подстроке (contains)
    BY_START_WITH = "b"  # Поиск по началу строки (startswith)
    BY_EXACT_MATCH = "e"  # Точное совпадение (exact)

    # Специфичные типы поиска для книг
    BY_AUTHOR = "a"  # Поиск по автору
    BY_SERIES = "s"  # Поиск по серии
    BY_AUTHOR_AND_SERIES = "as"  # Поиск по автору и серии
    BY_GENRE = "g"  # Поиск по жанру
    BY_USER = "u"  # Поиск по пользователю (книжная полка)
    DOUBLES = "d"  # Поиск дубликатов
    BY_ID = "i"  # Поиск по ID книги
    #
    # # Классовые переменные для группировки
    # COMMON_TYPES = (BY_SUBSTRING, BY_START_WITH, BY_EXACT_MATCH)
    #
    # BOOK_SEARCH_TYPES = (
    #     BY_AUTHOR,
    #     BY_SERIES,
    #     BY_AUTHOR_AND_SERIES,
    #     BY_GENRE,
    #     BY_USER,
    #     DOUBLES,
    #     BY_ID,
    # )
    #
    # @classmethod
    # def is_valid(cls, value: str) -> bool:
    #     """Проверяет, является ли значение допустимым типом поиска."""
    #     try:
    #         cls(value)
    #         return True
    #     except ValueError:
    #         return False
    #
    # @property
    # def description(self) -> str:
    #     """Возвращает человеко-читаемое описание типа поиска."""
    #     descriptions = {
    #         self.BY_SUBSTRING: "Поиск по подстроке",
    #         self.BY_START_WITH: "Поиск по началу строки",
    #         self.BY_EXACT_MATCH: "Точное совпадение",
    #         self.BY_AUTHOR: "Поиск по автору",
    #         self.BY_SERIES: "Поиск по серии",
    #         self.BY_AUTHOR_AND_SERIES: "Поиск по автору и серии",
    #         self.BY_GENRE: "Поиск по жанру",
    #         self.BY_USER: "Поиск по книжной полке пользователя",
    #         self.DOUBLES: "Поиск дубликатов",
    #         self.BY_ID: "Поиск по ID книги",
    #     }
    #     return descriptions.get(self, "Неизвестный тип поиска")


def extract_fb2_cover(
    file: BytesIO, original_filename: str, mimetype: str
) -> bytes | None:
    if config.SOPDS_FB2SAX:
        parser = FB2sax(file, original_filename)
    else:
        parser = FB2(file)
    # parser.parse()
    return parser.extract_cover()


def get_fb2_parser_factory(file: BytesIO, original_filename: str, mimetype: Mimetype):
    pass


def unzip_fb2_service(file: BytesIO) -> BytesIO:
    """Распаковывает содержимое файла из zip архива.

    Args:
        file(BytesIO): содержимое файла

    Returns:
        BytesIO: Распакованное из zip содержимое, если оно было упаковано в zip.
        В противном случае возвращается переданное содержимое без изменений.

    Raises:
        Выбрасывает исключение, если внутри переданного zip архива находится
        более одного файла.

    """
    if not zipfile.is_zipfile(file):
        return file

    content = BytesIO()

    with zipfile.ZipFile(file, "r") as z:
        if len(z.infolist()) > 1:
            raise Exception("Archive contains more than 1 files!")
        fn = z.namelist()[0]
        with z.open(fn, "r") as d:
            content.write(d.read())
    return content
