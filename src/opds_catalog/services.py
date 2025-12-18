# Сервисные функции opds_catalog
from io import BytesIO
from book_tools.format.mimetype import Mimetype
from book_tools.format.parsers import FB2, FB2sax
from constance import config
import os
import zipfile


def extract_fb2_cover(file: BytesIO, original_filename: str, mimetype: str):
    if config.SOPDS_FB2SAX:
        parser = FB2sax(file, original_filename)
    else:
        parser = FB2(file, original_filename, mimetype)
    # parser.parse()
    return parser.extract_cover()


def get_fb2_parser_factory(file: BytesIO, original_filename: str, mimetype: Mimetype):
    pass


def unzip_fb2_service(file: BytesIO) -> BytesIO:
    """
    Распаковывает содержимое файла из zip архива.

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


def detect_mime_by_suffix(filename: str) -> str:
    """Быстрое определение mimetype по суффиксу файла"""
    _, fmt = os.path.splitext(filename)

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


def detect_mime_service(file: BytesIO, original_filename: str):
    """Определение mimetype файла"""
    FB2_ROOT = "FictionBook"
    mime = detect_mime_by_suffix(original_filename)

    # try:
    with suppress(Exception):
        if mime == Mimetype.XML:
            if FB2_ROOT == __xml_root_tag(file):
                return Mimetype.FB2
        elif mime == Mimetype.ZIP:
            with zipfile.ZipFile(file) as zip_file:
                if not zip_file.testzip():
                    infolist = list_zip_file_infos(zip_file)
                    if len(infolist) == 1:
                        if FB2_ROOT == __xml_root_tag(zip_file.open(infolist[0])):
                            return Mimetype.FB2_ZIP
                    with suppress(Exception):
                        with zip_file.open("mimetype") as mimetype_file:
                            if (
                                mimetype_file.read(30).decode().rstrip("\n\r")
                                == Mimetype.EPUB
                            ):
                                return Mimetype.EPUB
                    # except Exception:
                    #     pass
        elif mime == Mimetype.OCTET_STREAM:
            mobiflag = file.read(68)
            mobiflag = mobiflag[60:]
            if mobiflag.decode() == "BOOKMOBI":
                return Mimetype.MOBI
    # except Exception:
    #     pass

    return mime
