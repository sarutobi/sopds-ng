# Сервисные функции opds_catalog
from io import BytesIO
from book_tools.format.mimetype import Mimetype
from book_tools.format.parsers import FB2, FB2sax
from constance import config


def extract_fb2_cover(file: BytesIO, original_filename: str, mimetype: Mimetype):
    if config.SOPDS_FB2SAX:
        parser = FB2sax(file, original_filename)
    else:
        parser = FB2(file, original_filename, mimetype)
    # parser.parse()
    return parser.extract_cover()
