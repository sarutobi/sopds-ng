# Сервисы для работы с электронными книгами
from io import BytesIO

from .format.bookfile import BookFile

# from .format.fb2sax import FB2sax
from .format.parsers import FB2Base
from .format.mimetype import Mimetype


def extract_fb2_metadata_service(data: BytesIO, original_filename: str) -> BookFile:
    """
    Извлечение метаданных книги в формате fb2

    Args:
        data(BytesIO): Содержимое книги fb2

    Returns:
        BookFile: извлеченные метаданные книги

    Raises:
        FB2StructureException

    """
    parser = FB2Base(data, original_filename, Mimetype.FB2)
    book_file = BookFile(data, original_filename, Mimetype.FB2)
    book_file.mimetype = Mimetype.FB2
    book_file.__set_title__(parser.title)
    book_file.description = parser.description
    print(parser.authors)
    for a in parser.authors:
        name, sortkey = a
        book_file.__add_author__(name, sortkey)
    print(book_file.authors)

    for t in parser.tags:
        book_file.__add_tag__(t)

    book_file.series_info = parser.series_info
    book_file.language_code = parser.language_code
    book_file.__set_docdate__(parser.docdate)
    return book_file
