# import magic
import logging
import os
import zipfile
from contextlib import suppress
from io import BytesIO
from xml import sax

from book_tools.format.bookfile import BookFile
from book_tools.format.mimetype import Mimetype
from book_tools.format.util import list_zip_file_infos
from book_tools.mime_detector import detect_mime_service
from book_tools.services import create_bookfile_service

# from constance import config

logger = logging.getLogger(__name__)


class mime_detector:
    @staticmethod
    def fmt(fmt):
        if fmt.lower() == "xml":
            return Mimetype.XML
        elif fmt.lower() == "fb2":
            return Mimetype.FB2
        elif fmt.lower() == "epub":
            return Mimetype.EPUB
        elif fmt.lower() == "mobi":
            return Mimetype.MOBI
        elif fmt.lower() == "zip":
            return Mimetype.ZIP
        elif fmt.lower() == "pdf":
            return Mimetype.PDF
        # elif fmt.lower() == "doc" or fmt.lower() == "docx":
        elif fmt.lower() in ("doc", "docx"):
            return Mimetype.MSWORD
        elif fmt.lower() == "djvu":
            return Mimetype.DJVU
        elif fmt.lower() == "txt":
            return Mimetype.TEXT
        elif fmt.lower() == "rtf":
            return Mimetype.RTF
        # else:
        return Mimetype.OCTET_STREAM

    @staticmethod
    def file(filename):
        (n, e) = os.path.splitext(filename)
        return mime_detector.fmt(e[1:])


# def detect_mime(file, original_filename):
#     FB2_ROOT = "FictionBook"
#     mime = mime_detector.file(original_filename)
#
#     # try:
#     with suppress(Exception):
#         if mime == Mimetype.XML:
#             if FB2_ROOT == __xml_root_tag(file):
#                 return Mimetype.FB2
#         elif mime == Mimetype.ZIP:
#             with zipfile.ZipFile(file) as zip_file:
#                 if not zip_file.testzip():
#                     infolist = list_zip_file_infos(zip_file)
#                     if len(infolist) == 1:
#                         if FB2_ROOT == __xml_root_tag(zip_file.open(infolist[0])):
#                             return Mimetype.FB2_ZIP
#                     with suppress(Exception):
#                         with zip_file.open("mimetype") as mimetype_file:
#                             if (
#                                 mimetype_file.read(30).decode().rstrip("\n\r")
#                                 == Mimetype.EPUB
#                             ):
#                                 return Mimetype.EPUB
#                     # except Exception:
#                     #     pass
#         elif mime == Mimetype.OCTET_STREAM:
#             mobiflag = file.read(68)
#             mobiflag = mobiflag[60:]
#             if mobiflag.decode() == "BOOKMOBI":
#                 return Mimetype.MOBI
#     # except Exception:
#     #     pass
#
#     return mime


def create_bookfile(path, original_filename=None) -> BookFile:
    """Извлечение метаданных электронной книги.

    Args:
        path: Путь к файлу (строка) или file-like объект (BytesIO).
        original_filename: Имя файла (обязательно если path — file-like).

    Returns:
        BookFile: извлеченные метаданные книги.
    """
    if isinstance(path, str):
        # If path is a string, open fd and pass raw (без BytesIO)
        if original_filename is None:
            original_filename = os.path.basename(path)
        logger.info(f"Read {original_filename} content from file system")
        fd = open(path, "rb")
        try:
            return create_bookfile_service(BytesIO(fd.read()), original_filename)
        finally:
            fd.close()
    else:
        # File-like object (BytesIO) — pass through directly
        if original_filename is None:
            raise ValueError("original_filename is required for file-like objects")
        data = BytesIO(path.read())
        return create_bookfile_service(data, original_filename)


# def __xml_root_tag(file):
#     class XMLRootFound(Exception):
#         def __init__(self, name):
#             self.name = name
#
#     class RootTagFinder(sax.handler.ContentHandler):
#         def startElement(self, name, attributes):
#             raise XMLRootFound(name)
#
#     try:
#         sax.parse(file, RootTagFinder())
#     except XMLRootFound as e:
#         return e.name
#     return None
