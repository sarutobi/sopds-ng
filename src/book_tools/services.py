# Сервисы для работы с электронными книгами
from io import BytesIO
import zipfile

from .format.bookfile import BookFile

# from .format.fb2sax import FB2sax
from .format.parsers import FB2
from .format.mimetype import Mimetype


def extract_fb2_metadata_service(data: BytesIO, original_filename: str) -> BookFile:
    """
    Извлечение метаданных книги в формате fb2

    Args:
        data(BytesIO): Содержимое книги fb2. Может быть упковано в формат zip

    Returns:
        BookFile: извлеченные метаданные книги

    Raises:
        FB2StructureException

    """
    if zipfile.is_zipfile(data):
        with zipfile.ZipFile(data, "r") as z:
            if len(z.infolist()) > 1:
                raise Exception("Incorrect fb2 zip archive!")
            fn = z.namelist()[0]
            with z.open(fn, "r") as d:
                content = BytesIO()
                content.write(d.read())

    else:
        content = data

    parser = FB2(content, original_filename, Mimetype.FB2)
    book_file = BookFile(data, original_filename, Mimetype.FB2)
    book_file.mimetype = Mimetype.FB2
    book_file.__set_title__(parser.title)
    book_file.description = parser.description
    for a in parser.authors:
        name, sortkey = a
        book_file.__add_author__(name, sortkey)

    for t in parser.tags:
        book_file.__add_tag__(t)

    book_file.series_info = parser.series_info
    book_file.language_code = parser.language_code
    book_file.__set_docdate__(parser.docdate)
    return book_file
