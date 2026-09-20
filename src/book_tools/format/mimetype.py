class Mimetype:
    """Описание mime-type."""

    OCTET_STREAM = "application/octet-stream"
    XML = "application/xml"
    ZIP = "application/zip"

    EPUB = "application/epub+zip"
    FB2 = "application/fb2+xml"
    FB2_ZIP = "application/fb2+zip"
    PDF = "application/pdf"
    MSWORD = "application/msword"
    MOBI = "application/x-mobipocket-ebook"
    DJVU = "image/vnd.djvu"
    TEXT = "text/plain"
    RTF = "text/rtf"

    FORMAT_MIME_MAP: dict[str, str] = {
        "xml": XML,
        "fb2": FB2,
        "epub": EPUB,
        "mobi": MOBI,
        "zip": ZIP,
        "pdf": PDF,
        "doc": MSWORD,
        "docx": MSWORD,
        "djvu": DJVU,
        "txt": TEXT,
        "rtf": RTF,
    }

    @staticmethod
    def mime_by_format(fmt: str) -> str:
        """Получение MIME-типа по строке формата (без точки)."""
        return Mimetype.FORMAT_MIME_MAP.get(fmt.lower(), Mimetype.OCTET_STREAM)

    @staticmethod
    def mime_by_suffix(ext: str) -> str:
        """Получение MIME-типа по суффиксу (с точкой)."""
        # Убираем точку для поиска в FORMAT_MIME_MAP
        fmt = ext.lower().lstrip(".")
        return Mimetype.FORMAT_MIME_MAP.get(fmt, Mimetype.OCTET_STREAM)
