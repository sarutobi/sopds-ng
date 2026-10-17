"""Адаптер для преобразования сырых данных INPX в унифицированные метаданные книги."""

from opds_catalog.inpx_parser import (
    sAuthor,
    sDate,
    sGenre,
    sLang,
    sSeries,
    sSerNo,
    sTitle,
)
from opds_catalog.services.dto import AuthorMetadata, BookMetadata, SeriesMetadata


def to_book_metadata(raw_data: dict, rel_path: str) -> BookMetadata:
    """Преобразует словарь данных из Inpx.parse в BookMetadata.

    :param raw_data: Словарь с данными одной записи из INPX.
    :param rel_path: Относительный путь к архиву/каталогу.
    :returns: Объект BookMetadata.
    """
    # Авторы
    authors_raw = raw_data.get(sAuthor, [])
    authors = [
        AuthorMetadata(full_name=name.strip()) for name in authors_raw if name.strip()
    ]

    # Жанры
    genres_raw = raw_data.get(sGenre, [])
    genres = [genre.strip() for genre in genres_raw if genre.strip()]

    # Серии
    series_raw = raw_data.get(sSeries, [])
    series = []
    ser_no_str = raw_data.get(sSerNo, "0").strip()
    try:
        ser_no = int(ser_no_str) if ser_no_str else 0
    except ValueError:
        ser_no = 0

    for s_name in series_raw:
        name = s_name.strip()
        if name:
            series.append(SeriesMetadata(name=name, series_no=ser_no))

    return BookMetadata(
        title=raw_data.get(sTitle, "").strip(),
        authors=authors,
        genres=genres,
        series=series,
        docdate=raw_data.get(sDate, "").strip(),
        lang=raw_data.get(sLang, "ru").strip(),
        annotation="",  # В INPX обычно нет аннотации
    )
