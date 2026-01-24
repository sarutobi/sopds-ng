# Сервисы для работы с электронными книгами
import logging
from lxml.etree import XMLSyntaxError
import os
import zipfile
from abc import ABC, abstractmethod
from contextlib import suppress
from io import BytesIO

from lxml import etree

from .format.bookfile import BookFile
from .format.mimetype import Mimetype

from .format.parsers import FB2

logger = logging.getLogger(__name__)


def create_bookfile_service(data: BytesIO, original_filename: str) -> BookFile:
    """
    Извлечение метаданных электронной книги

    Args:
        data(BytesIO): Содержимое файла электронной книги

    Returns:
        BookFile: извлеченные метаданные книги

    Raises:
        FB2StructureException

    """
    logger.info(f"Attempt to extract metadata from {original_filename}")
    logger.debug(f"Content size: {len(data.getvalue())}")
    if zipfile.is_zipfile(data):
        logger.info(f"{original_filename} id ZIP file")
        with zipfile.ZipFile(data, "r") as z:
            if len(z.infolist()) > 1:
                raise Exception("Incorrect fb2 zip archive!")
            fn = z.namelist()[0]
            with z.open(fn, "r") as d:
                content = BytesIO()
                content.write(d.read())

    else:
        content = data

    parser = FB2(content)
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


class MimetypeValidator(ABC):
    """Определяет соответствие файла определенному mimetype"""

    def __init__(self, mimetype: str):
        self.mimetype = mimetype

    @abstractmethod
    def is_valid(self, filename: str, content: BytesIO) -> bool: ...

    def filetype(self) -> str:
        return self.mimetype


class FB2MimeValidator(MimetypeValidator):
    """Проверка на сответствие типу FB2"""

    def __init__(self):
        super().__init__(Mimetype.FB2)

    def is_valid(self, filename, content) -> bool:
        with suppress(XMLSyntaxError):
            parser = etree.XMLParser(ns_clean=True)
            root = etree.parse(content, parser=parser).getroot()
            return etree.QName(root).localname == "FictionBook"
        return False


class FB2ZipMimeValidator(MimetypeValidator):
    """Проверка на соотвествие типу FB2+Zip"""

    def __init__(self):
        super().__init__(Mimetype.FB2_ZIP)

    def is_valid(self, filename, content) -> bool:
        with suppress(zipfile.BadZipFile):
            with zipfile.ZipFile(content) as zip_file:
                if zip_file.testzip():
                    return False

                if len(zip_file.infolist()) > 1:
                    return False

                fn = zip_file.namelist()[0]
                with zip_file.open(fn, "r") as f:
                    content = BytesIO()
                    content.write(f.read())
            content.seek(0)
            parser = etree.XMLParser(ns_clean=True)
            root = etree.parse(content, parser=parser).getroot()
            return etree.QName(root).localname == "FictionBook"

        return False


class EPUBMimeValidator(MimetypeValidator):
    """Проверка на соотвествие типу EPUB"""

    def __init__(self):
        super().__init__(Mimetype.EPUB)

    def is_valid(self, filename, content) -> bool:
        with suppress(Exception):
            with zipfile.ZipFile(content) as zip_file:
                with zip_file.open("mimetype") as mimetype_file:
                    return (
                        mimetype_file.read(30).decode().rstrip("\n\r") == Mimetype.EPUB
                    )
        return False


class MobiMimeValidator(MimetypeValidator):
    """Проверка на соотвествие типу Mobi"""

    def __init__(self):
        super().__init__(Mimetype.MOBI)

    def is_valid(self, filename, content) -> bool:
        mobiflag = content.getvalue()[60:68]
        return mobiflag.decode() == "BOOKMOBI"


class SuffixMimeValidator(MimetypeValidator):
    """Упрощенный валидатор, выставляет соответствие типу по суффиксу файла"""

    def __init__(self, suffixes: list[str], mimetype: str):
        super().__init__(mimetype)
        self.suffixes = suffixes

    def is_valid(self, filename, content) -> bool:
        _, s = os.path.splitext(filename)
        return s in self.suffixes


class GenericMimeValidator(MimetypeValidator):
    """Обобщенный тип файла OCTET_STREAM"""

    def __init__(self):
        super().__init__(Mimetype.OCTET_STREAM)

    def is_valid(self, filename, content) -> bool:
        return True


def detect_mime_service(file: BytesIO, original_filename: str) -> str:
    """
    Определение mimetype файла. Определение идет по содержимому и/или суффиксу
    файла. Если нельзя определить конкретный тип, то возвращается обобщенный
    тип application/octet-stream

    Args:
        file(BytesIO): Содержимое файла

        original_filename(str): Имя файла

    Returns:
        str Установленный Mimetype файла.
    """
    logger.info(f"Detecting mimetype of {original_filename}")
    # Перечень известных валидаторов. Должны быть описаны от конкретных к
    # обобощенным.
    detectors: list[MimetypeValidator] = [
        FB2MimeValidator(),
        FB2ZipMimeValidator(),
        EPUBMimeValidator(),
        MobiMimeValidator(),
        SuffixMimeValidator(
            [
                ".xml",
            ],
            Mimetype.XML,
        ),
        SuffixMimeValidator(
            [
                ".zip",
            ],
            Mimetype.ZIP,
        ),
        SuffixMimeValidator(
            [
                ".pdf",
            ],
            Mimetype.PDF,
        ),
        SuffixMimeValidator([".doc", ".docx"], Mimetype.MSWORD),
        SuffixMimeValidator(
            [
                ".djvu",
            ],
            Mimetype.DJVU,
        ),
        SuffixMimeValidator(
            [
                ".txt",
            ],
            Mimetype.TEXT,
        ),
        SuffixMimeValidator(
            [
                ".rtf",
            ],
            Mimetype.RTF,
        ),
    ]

    for v in detectors:
        logger.info(f"Check that {original_filename} is {v.mimetype}")
        if v.is_valid(original_filename, file):
            logger.info("Check successful")
            return v.filetype()

    logger.info(f"{original_filename} is {Mimetype.OCTET_STREAM}")
    return Mimetype.OCTET_STREAM
