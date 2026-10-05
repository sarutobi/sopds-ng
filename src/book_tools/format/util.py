import re

strip_symbols = " »«'\"&\n-.#\\`"


def list_zip_file_infos(zipfile):
    return [info for info in zipfile.infolist() if not info.filename.endswith("/")]


def normalize_string(text: str) -> str | None:
    """Убирает повторяющиеся пробелы и переносы строки во входной строке"""
    if text is None:
        return None
    return re.sub(r"\s+", " ", text.strip())
