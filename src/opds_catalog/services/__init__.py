# Сервисные функции opds_catalog
import zipfile
from io import BytesIO

from constance import config

from book_tools.format.mimetype import Mimetype
from book_tools.format.parsers import FB2, FB2sax


def extract_fb2_cover(
    file: BytesIO, original_filename: str, mimetype: str
) -> bytes | None:
    if config.SOPDS_FB2SAX:
        parser = FB2sax(file, original_filename)
    else:
        parser = FB2(file, original_filename, mimetype)
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
