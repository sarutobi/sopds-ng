# Сервисы для работы с электронными книгами
from datetime import date
from io import BytesIO
import logging
from typing import Callable, Optional
import zipfile

from .exceptions import (
    UnsupportedFormatException,
    UnsupportedFileType,
    FB2StructureException,
    EpubStructureException,
    EbookParserException,
)
from .format.bookfile import BookFile
from .format.ebook_parsers.dto import Author, BookMetadata, Cover, Series
from .format.mimetype import Mimetype
from .format.parsers import FB2, EpubParser
from .format.epub import EPub as EPubOld
from .mime_detector import detect_mime_service
from .pymobi.mobi import BookMobi

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Parser registry
# ---------------------------------------------------------------------------

_parsers: dict[str, Callable] = {}


def register_parser(mimetype: str, parser_fn: Callable) -> None:
    """Register a parser function for the given mimetype."""
    _parsers[mimetype] = parser_fn


def get_parser(mimetype: str) -> Callable:
    """Look up a parser by mimetype.

    Raises UnsupportedFormatException if no parser is registered.
    """
    parser = _parsers.get(mimetype)
    if parser is None:
        raise UnsupportedFormatException(f"No parser registered for {mimetype}")
    return parser


# ---------------------------------------------------------------------------
# BookMetadata → BookFile converter
# ---------------------------------------------------------------------------


def book_metadata_to_bookfile(
    meta: BookMetadata,
    file,
    original_filename: str,
    mimetype: str,
) -> BookFile:
    """Convert a BookMetadata DTO to the legacy BookFile container.

    This ensures backwards compatibility for callers that still use
    BookFile attributes directly.
    """
    book_file = BookFile(file, original_filename, mimetype)

    book_file.__set_title__(meta.title)

    for author in meta.authors:
        name_parts = [
            p for p in (author.first_name, author.middle_name, author.last_name) if p
        ]
        name = " ".join(name_parts)
        sortkey = author.last_name or name.split()[-1] if name else ""
        book_file.__add_author__(name, sortkey)

    for genre in meta.genres:
        book_file.__add_tag__(genre)

    if meta.series is not None:
        book_file.series_info = {
            "title": meta.series.name,
            "index": str(meta.series.series_no),
        }

    if meta.language:
        book_file.language_code = meta.language

    if meta.description:
        book_file.description = meta.description

    if meta.docdate:
        book_file.__set_docdate__(meta.docdate)
    elif meta.publication_date:
        book_file.__set_docdate__(meta.publication_date.isoformat())

    return book_file


# ---------------------------------------------------------------------------
# Parser functions (each returns BookMetadata)
# ---------------------------------------------------------------------------


def parse_fb2(file_obj, original_filename: str) -> BookMetadata:
    """Parse FB2 file and return BookMetadata."""
    try:
        parser = FB2(file_obj)
    except FB2StructureException:
        raise
    except Exception as e:
        raise FB2StructureException(e) from e
    return _fb2_parser_to_metadata(parser, file_obj, original_filename)


def _fb2_parser_to_metadata(
    parser: FB2,
    file_obj,
    original_filename: str,
) -> BookMetadata:
    """Convert an FB2 parser result to BookMetadata."""
    title = parser.title or original_filename

    authors: list[Author] = []
    for name, sortkey in parser.authors:
        parts = name.split()
        first_name = parts[0] if parts else ""
        last_name = parts[-1] if len(parts) > 1 else ""
        middle_name = " ".join(parts[1:-1]) if len(parts) > 2 else None
        authors.append(
            Author(first_name=first_name, last_name=last_name, middle_name=middle_name)
        )

    series: Optional[Series] = None
    if parser.series_info:
        series = Series(
            name=parser.series_info.get("title", ""),
            series_no=int(parser.series_info.get("index", 0) or 0),
        )

    genres = parser.tags or []
    language = parser.language_code or ""

    description: Optional[str] = None
    if parser.description is not None:
        desc = parser.description
        if isinstance(desc, bytes):
            description = desc.decode("utf-8")
        else:
            description = desc

    docdate: str = parser.docdate or ""

    return BookMetadata(
        title=title,
        authors=authors,
        series=series,
        genres=genres,
        language=language,
        description=description,
        docdate=docdate,
    )


def parse_fb2_zip(file_obj, original_filename: str) -> BookMetadata:
    """Parse FB2 file stored inside a ZIP archive."""
    with zipfile.ZipFile(file_obj, "r") as z:
        if len(z.infolist()) != 1:
            raise FB2StructureException("Incorrect fb2 zip archive!")
        fn = z.namelist()[0]
        with z.open(fn, "r") as d:
            content = BytesIO()
            content.write(d.read())
    content.seek(0)
    return parse_fb2(content, fn)


def parse_epub(file_obj, original_filename: str) -> BookMetadata:
    """Parse EPUB file and return BookMetadata (uses legacy EPub parser)."""
    try:
        epub = EPubOld(file_obj, original_filename)
    except Exception as e:
        # Любые исключения EPub -> EpubStructureException
        raise EpubStructureException(str(e)) from e

    authors: list[Author] = []
    for a in epub.authors:
        # EPub хранит name как полное имя автора ("Александр  Мирер")
        # сохраняем в DTO как first_name, без last_name — конвертер сам выделит sortkey
        authors.append(Author(first_name=a["name"]))

    series: Optional[Series] = None
    if epub.series_info:
        idx = epub.series_info.get("index")
        series = Series(
            name=epub.series_info.get("title", ""),
            series_no=int(idx) if idx else 0,
        )

    docdate: str = epub.docdate or ""

    desc: str | None = None
    if epub.description:
        desc = (
            epub.description
            if isinstance(epub.description, str)
            else epub.description.decode("utf-8")
        )

    return BookMetadata(
        title=epub.title,
        authors=authors,
        series=series,
        genres=epub.tags or [],
        language=epub.language_code or "",
        description=desc,
        docdate=docdate,
    )


def parse_mobi(file_obj, original_filename: str) -> BookMetadata:
    """Parse MOBI file and return BookMetadata via BookMobi."""
    try:
        bm = BookMobi(file_obj)
    except Exception as e:
        raise EbookParserException(f"mobi parsing failed: {e}") from e

    title = bm["title"] or original_filename

    authors: list[Author] = []
    raw_author = bm["author"] or ""
    if raw_author:
        parts = raw_author.split()
        first_name = parts[0] if parts else ""
        last_name = parts[-1] if len(parts) > 1 else ""
        middle_name = " ".join(parts[1:-1]) if len(parts) > 2 else None
        authors.append(
            Author(first_name=first_name, last_name=last_name, middle_name=middle_name)
        )

    genres = (bm["subject"] or []) if bm["subject"] else []

    description: Optional[str] = bm["description"] or None

    docdate: str = ""
    mod_date = bm["modificationDate"]
    if mod_date:
        try:
            if hasattr(mod_date, "strftime"):
                docdate = mod_date.strftime("%Y-%m-%d")
            else:
                docdate = str(mod_date)
        except (ValueError, TypeError):
            pass

    return BookMetadata(
        title=title,
        authors=authors,
        genres=genres,
        language="",
        description=description,
        docdate=docdate,
    )


def parse_dummy(file_obj, original_filename: str) -> BookMetadata:
    """Return minimal BookMetadata for unsupported formats."""
    return BookMetadata(
        title=original_filename,
        authors=[],
        genres=[],
    )


# ---------------------------------------------------------------------------
# Register parsers at import time
# ---------------------------------------------------------------------------

register_parser(Mimetype.FB2, parse_fb2)
register_parser(Mimetype.FB2_ZIP, parse_fb2_zip)
register_parser(Mimetype.EPUB, parse_epub)
register_parser(Mimetype.MOBI, parse_mobi)
register_parser(Mimetype.TEXT, parse_dummy)
register_parser(Mimetype.PDF, parse_dummy)
register_parser(Mimetype.MSWORD, parse_dummy)
register_parser(Mimetype.RTF, parse_dummy)
register_parser(Mimetype.DJVU, parse_dummy)


# ---------------------------------------------------------------------------
# create_bookfile_service (BytesIO entry point)
# ---------------------------------------------------------------------------


def create_bookfile_service(data: BytesIO, original_filename: str) -> BookFile:
    """Извлечение метаданных электронной книги через parser registry.

    Args:
        data(BytesIO): Содержимое файла электронной книги
        original_filename(str): Имя файла

    Returns:
        BookFile: извлеченные метаданные книги

    Raises:
        UnsupportedFileType — если для MIME-типа нет зарегистрированного парсера
        FB2StructureException
    """
    logger.info(f"Attempt to extract metadata from {original_filename}")
    logger.debug(f"Content size: {len(data.getvalue())}")
    mimetype = detect_mime_service(data, original_filename)

    # Normalise FB2_ZIP → FB2 для поиска парсера и распаковываем ZIP
    content_data: BytesIO
    content_mimetype: str
    if mimetype == Mimetype.FB2_ZIP:
        content_mimetype = Mimetype.FB2
        with zipfile.ZipFile(data, "r") as z:
            if z.testzip():
                raise FB2StructureException("corrupted zip archive")
            if len(z.infolist()) != 1:
                raise FB2StructureException("Incorrect fb2 zip archive!")
            fn = z.namelist()[0]
            with z.open(fn, "r") as d:
                content_data = BytesIO()
                content_data.write(d.read())
        content_data.seek(0)
    else:
        content_mimetype = mimetype
        content_data = data

    try:
        parser_fn = get_parser(content_mimetype)
    except UnsupportedFormatException as e:
        raise UnsupportedFileType(content_mimetype, original_filename) from e

    metadata = parser_fn(content_data, original_filename)
    return book_metadata_to_bookfile(
        metadata, data, original_filename, content_mimetype
    )
