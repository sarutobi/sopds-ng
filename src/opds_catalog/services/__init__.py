"""Сервисные функции opds_catalog."""

import zipfile
from enum import StrEnum
from io import BytesIO

from book_tools.format.mimetype import Mimetype
from book_tools.format.parsers import FB2


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


def extract_fb2_cover(
    file: BytesIO, original_filename: str, mimetype: str
) -> bytes | None:
    parser = FB2(file)
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
