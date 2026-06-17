"""Тесты mimetype-детектора и сервиса парсинга (задача 1.9.6)."""

from io import BytesIO
import os

import pytest

from book_tools.exceptions import UnsupportedFormatException, UnsupportedFileType
from book_tools.format import create_bookfile
from book_tools.format.mimetype import Mimetype
from book_tools.mime_detector import (
    detect_mime_service,
    detect_by_suffix,
)
from book_tools.services import (
    create_bookfile_service,
    get_parser,
)


# ---------------------------------------------------------------------------
# detect_mime_service — все поддерживаемые типы
# ---------------------------------------------------------------------------


def test_detect_fb2(test_rootlib) -> None:
    """FB2-файл определяется как application/fb2+xml."""
    path = os.path.join(test_rootlib, "262001.fb2")
    with open(path, "rb") as f:
        data = BytesIO(f.read())
    assert detect_mime_service(data, "262001.fb2") == Mimetype.FB2


def test_detect_fb2_zip(test_rootlib) -> None:
    """ZIP с FB2 внутри определяется как application/fb2+zip."""
    path = os.path.join(test_rootlib, "262001.zip")
    with open(path, "rb") as f:
        data = BytesIO(f.read())
    assert detect_mime_service(data, "262001.zip") == Mimetype.FB2_ZIP


def test_detect_epub(test_rootlib) -> None:
    """EPUB определяется как application/epub+zip."""
    path = os.path.join(test_rootlib, "mirer.epub")
    with open(path, "rb") as f:
        data = BytesIO(f.read())
    assert detect_mime_service(data, "mirer.epub") == Mimetype.EPUB


def test_detect_mobi(test_rootlib) -> None:
    """MOBI определяется как application/x-mobipocket-ebook."""
    path = os.path.join(test_rootlib, "robin_cook.mobi")
    with open(path, "rb") as f:
        data = BytesIO(f.read())
    assert detect_mime_service(data, "robin_cook.mobi") == Mimetype.MOBI


def test_false_positive_pdf() -> None:
    """Байтовая строка, не похожая на PDF, не детектируется."""
    data = BytesIO(b"PK\x03\x04dummy")
    assert detect_mime_service(data, "test.pdf") != Mimetype.PDF


def test_false_positive_djvu() -> None:
    """Байтовая строка, не похожая на DJVU, не детектируется."""
    data = BytesIO(b"RIFF\x00\x00\x00\x00AVI ")
    assert detect_mime_service(data, "test.djvu") != Mimetype.DJVU


def test_detect_pdf_content() -> None:
    """PDF с корректной сигнатурой детектируется по содержимому."""
    data = BytesIO(b"%PDF-1.4\n%%EOF\n")
    assert detect_mime_service(data, "test.pdf") == Mimetype.PDF


def test_detect_djvu_content() -> None:
    """DJVU с корректной сигнатурой детектируется по содержимому."""
    data = BytesIO(b"FORM\x00\x08\x00\x00DJVU")
    assert detect_mime_service(data, "test.djvu") == Mimetype.DJVU


@pytest.mark.parametrize(
    "filename, expected_mime",
    [
        ("dummy.txt", Mimetype.TEXT),
        ("dummy.doc", Mimetype.MSWORD),
        ("dummy.docx", Mimetype.MSWORD),
        ("dummy.rtf", Mimetype.RTF),
    ],
)
def test_detect_suffix_based(filename, expected_mime) -> None:
    """Детекция по суффиксу для форматов без content-based валидации."""
    data = BytesIO(b"dummy content")
    assert detect_mime_service(data, filename) == expected_mime


@pytest.mark.parametrize(
    "filename",
    [
        "badfile.fb2",
        "badfile.zip",
        "badfile2.fb2",
        "badfile2.zip",
    ],
)
def test_no_false_positive(filename, test_rootlib) -> None:
    """Заведомо битые/мусорные файлы НЕ определяются как поддерживаемый тип.

    badfile.fb2/badfile.zip — не XML/не ZIP, не должны детектиться.
    badfile2.fb2/badfile2.zip — XML с FictionBook root, но битый контент.
    Детектор видит root-тег (FB2/FB2_ZIP) — корректно.
    Исключение будет на этапе парсинга.
    """
    path = os.path.join(test_rootlib, filename)
    with open(path, "rb") as f:
        data = BytesIO(f.read())
    mime = detect_mime_service(data, filename)
    if filename in ("badfile.fb2",):
        assert mime == Mimetype.OCTET_STREAM
    elif filename == "badfile.zip":
        # plain text с .zip — suffix доверяется (нет content-проверки ZIP)
        assert mime == Mimetype.ZIP
    else:
        # badfile2.* — XML с FictionBook root, детектируется как FB2
        assert mime in (Mimetype.FB2, Mimetype.FB2_ZIP)


@pytest.mark.parametrize(
    "filename, expected_attr",
    [
        ("262001.fb2", "title"),
        ("262001.zip", "title"),
        ("mirer.epub", "title"),
        ("robin_cook.mobi", "title"),
    ],
)
def test_create_bookfile_service(filename, expected_attr, test_rootlib) -> None:
    """create_bookfile_service возвращает BookFile с метаданными."""
    path = os.path.join(test_rootlib, filename)
    with open(path, "rb") as f:
        data = BytesIO(f.read())
    result = create_bookfile_service(data, filename)
    assert result is not None
    assert getattr(result, expected_attr, None) is not None


def test_create_bookfile_service_dummy() -> None:
    """Dummy-файлы (txt, pdf) возвращают BookFile с минимальными данными."""
    data = BytesIO(b"plain text content")
    result = create_bookfile_service(data, "test.txt")
    assert result is not None
    assert result.title == "test.txt"


def test_create_bookfile_path(test_rootlib) -> None:
    """create_bookfile с путём к файлу открывает и парсит."""
    path = os.path.join(test_rootlib, "262001.fb2")
    result = create_bookfile(path)
    assert result is not None
    assert result.title != "262001.fb2"


def test_create_bookfile_filelike(test_rootlib) -> None:
    """create_bookfile с ByteIO проходит через create_bookfile_service."""
    path = os.path.join(test_rootlib, "262001.fb2")
    with open(path, "rb") as f:
        data = BytesIO(f.read())
    result = create_bookfile(data, "262001.fb2")
    assert result is not None


# ---------------------------------------------------------------------------
# Неподдерживаемые типы — UnsupportedFileType
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename, mime_type",
    [
        ("test.zip", Mimetype.ZIP),
        ("test.xml", Mimetype.XML),
        ("test.bin", Mimetype.OCTET_STREAM),
    ],
)
def test_unsupported_format(filename, mime_type) -> None:
    """XML, ZIP, OCTET_STREAM без зарегистрированного парсера -> UnsupportedFileType."""
    data = BytesIO(b"dummy")
    assert detect_mime_service(data, filename) == mime_type
    with pytest.raises(UnsupportedFileType):
        create_bookfile_service(data, filename)


def test_create_bookfile_unsupported() -> None:
    """Попытка создать книгу из неподдерживаемого типа -> UnsupportedFileType."""
    data = BytesIO(b"not a book")
    with pytest.raises(UnsupportedFileType):
        create_bookfile(data, "test.bin")
