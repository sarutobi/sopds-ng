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

    suffix_mime_mapper: dict[str, str] = {
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
    def mime_by_type(type: str) -> str:
        """Получение полного mime-type по закодированному."""
        return Mimetype.suffix_mime_mapper[type] or Mimetype.OCTET_STREAM
