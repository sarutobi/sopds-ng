# -*- coding: utf-8 -*-

from typing import Any

from django.utils.translation import gettext as _

from book_tools.format.util import strip_symbols
from opds_catalog.services.dto import AuthorMetadata, BookMetadata, SeriesMetadata


def to_book_metadata_raw(book_data: Any, filename: str) -> BookMetadata:
    """
    Преобразует данные из create_bookfile (BookData) в унифицированный BookMetadata.
    """
    # Title
    title = book_data.title.strip(strip_symbols) if book_data.title else filename

    # Annotation
    annotation = book_data.description or ""
    if isinstance(annotation, bytes):
        annotation = annotation.decode("utf8", errors="replace")
    annotation = annotation.strip(strip_symbols)

    # Language
    lang = (
        book_data.language_code.strip(strip_symbols) if book_data.language_code else ""
    )

    # Date
    docdate = book_data.docdate or ""

    # Authors normalization (Legacy logic: move last word to front if no comma)
    normalized_authors = []
    seen_authors = set()
    for a in book_data.authors:
        author_name = a.get("name", _("Unknown author")).strip(strip_symbols)
        if not author_name:
            continue

        # Legacy raw_scan logic: if no comma, treat last word as last_name
        if author_name.find(",") < 0:
            parts = author_name.split()
            author_name = (
                f"{parts[-1]} {' '.join(parts[:-1])}" if parts else author_name
            )

        if author_name not in seen_authors:
            normalized_authors.append(AuthorMetadata(full_name=author_name))
            seen_authors.add(author_name)

    # Genres normalization
    normalized_genres = [
        g.lower().strip(strip_symbols) for g in dict.fromkeys(book_data.tags) if g
    ]

    # Series normalization
    series_meta = []
    if book_data.series_info:
        series_title = book_data.series_info.get("title")
        if series_title:
            series_title = series_title.strip()
            s_no = book_data.series_info.get("index") or "0"
            series_no = int(s_no) if str(s_no).isdigit() else 0
            series_meta.append(SeriesMetadata(name=series_title, series_no=series_no))

    return BookMetadata(
        title=title,
        annotation=annotation,
        authors=normalized_authors,
        genres=normalized_genres,
        series=series_meta,
        docdate=docdate,
        lang=lang,
    )
