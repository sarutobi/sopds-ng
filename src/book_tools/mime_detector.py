"""Определение MIME-типа файла в две фазы: по суффиксу и по содержимому.

Содержит content-based валидаторы (без параметра filename),
детектор суффиксов и двухфазную функцию detect_mime_service.

Спроектирован как замена всей MIME-логики в services.py,
решая проблему циклических импортов.
"""

import logging
import os
from abc import ABC, abstractmethod
from contextlib import suppress
from io import BytesIO
import zipfile
from xml.parsers.expat import ParserCreate

from .format.mimetype import Mimetype

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Suffix → MIME mapping
# ---------------------------------------------------------------------------

_SUFFIX_MIME_MAP: dict[str, str] = {
    ".fb2": Mimetype.FB2,
    ".epub": Mimetype.EPUB,
    ".mobi": Mimetype.MOBI,
    ".pdf": Mimetype.PDF,
    ".doc": Mimetype.MSWORD,
    ".docx": Mimetype.MSWORD,
    ".djvu": Mimetype.DJVU,
    ".txt": Mimetype.TEXT,
    ".rtf": Mimetype.RTF,
    ".xml": Mimetype.XML,
    ".zip": Mimetype.ZIP,
}


# ---------------------------------------------------------------------------
# Base class for content-based validators
# ---------------------------------------------------------------------------


class MimetypeValidator(ABC):
    """Базовый класс для content-based валидаторов MIME.

    Все наследники реализуют is_valid(content), НЕ принимающий filename.
    """

    def __init__(self, mimetype: str):
        self.mimetype = mimetype

    @abstractmethod
    def is_valid(self, content) -> bool:
        """Проверяет, соответствует ли содержимое файла данному MIME-типу.

        Args:
            content: file-like object (BytesIO или raw fd).
                     Гарантированный seek(0) перед вызовом.

        Returns:
            True если содержимое соответствует типу.
        """


# ---------------------------------------------------------------------------
# Content-based validators (NO filename parameter)
# ---------------------------------------------------------------------------


class MobiContentValidator(MimetypeValidator):
    """Проверка MOBI: read(68), bytes[60:68] == b'BOOKMOBI'.

    Работает как с BytesIO, так и с raw fd (read/seek, не getvalue).
    """

    def __init__(self):
        super().__init__(Mimetype.MOBI)

    def is_valid(self, content) -> bool:
        content.seek(0)
        try:
            raw = content.read(68)
            return len(raw) >= 68 and raw[60:68] == b"BOOKMOBI"
        except Exception:
            return False
        finally:
            content.seek(0)


class EPUBContentValidator(MimetypeValidator):
    """Проверка EPUB: ZIP → чтение entry mimetype, сравнение строки."""

    def __init__(self):
        super().__init__(Mimetype.EPUB)

    def is_valid(self, content) -> bool:
        content.seek(0)
        try:
            with zipfile.ZipFile(content) as zf:
                with zf.open("mimetype") as mt:
                    return mt.read(30).decode().rstrip("\n\r") == Mimetype.EPUB
        except Exception:
            return False
        finally:
            content.seek(0)


class FB2ContentValidator(MimetypeValidator):
    """Проверка FB2 через expat (SAX), только первые 4096 байт, без DOM.

    Использует xml.parsers.expat.ParserCreate для поиска корневого тега.
    """

    def __init__(self):
        super().__init__(Mimetype.FB2)

    def is_valid(self, content) -> bool:
        content.seek(0)
        try:
            raw = content.read(4096)
            if not raw:
                return False
            return _check_fb2_root(raw)
        except Exception:
            return False
        finally:
            content.seek(0)


class PDFContentValidator(MimetypeValidator):
    """Проверка PDF: первые 5 байт == '%PDF-'."""

    def __init__(self):
        super().__init__(Mimetype.PDF)

    def is_valid(self, content) -> bool:
        content.seek(0)
        try:
            raw = content.read(5)
            return raw == b"%PDF-"
        except Exception:
            return False
        finally:
            content.seek(0)


class DJVUContentValidator(MimetypeValidator):
    """Проверка DJVU: FORM-заголовок с DJVU/DJVM идентификатором."""

    def __init__(self):
        super().__init__(Mimetype.DJVU)

    def is_valid(self, content) -> bool:
        content.seek(0)
        try:
            raw = content.read(12)
            if len(raw) < 12:
                return False
            return raw[:4] == b"FORM" and raw[8:12] in (b"DJVU", b"DJVM")
        except Exception:
            return False
        finally:
            content.seek(0)


class FB2ZipContentValidator(MimetypeValidator):
    """Проверка FB2+ZIP: ZIP → извлечение → expat (первые 4 КБ)."""

    def __init__(self):
        super().__init__(Mimetype.FB2_ZIP)

    def is_valid(self, content) -> bool:
        content.seek(0)
        try:
            with zipfile.ZipFile(content) as zf:
                if zf.testzip():
                    return False
                if len(zf.infolist()) != 1:
                    return False
                fn = zf.namelist()[0]
                with zf.open(fn, "r") as inner:
                    raw = inner.read(4096)
        except Exception:
            return False
        finally:
            content.seek(0)

        return _check_fb2_root(raw)


# ---------------------------------------------------------------------------
# Content detector list — order: cheapest first
# ---------------------------------------------------------------------------

_CONTENT_DETECTORS: list[MimetypeValidator] = [
    MobiContentValidator(),  # 68 bytes read — самый дешёвый
    PDFContentValidator(),  # 5 bytes read
    DJVUContentValidator(),  # 12 bytes read
    EPUBContentValidator(),  # ZIP-заголовок + 30 байт
    FB2ContentValidator(),  # expat, первые 4 КБ, без DOM
    FB2ZipContentValidator(),  # ZIP + expat — самый дорогой, последний
]


# ---------------------------------------------------------------------------
# Helper: expat-based FictionBook root tag check
# ---------------------------------------------------------------------------


def _check_fb2_root(raw: bytes) -> bool:
    """Проверяет, является ли корневой тег XML-фрагмента 'FictionBook'.

    Использует expat SAX-парсер, останавливается после первого элемента.
    """
    root_tag: list[str | None] = [None]

    def start_element(name: str, attrs: dict) -> None:
        root_tag[0] = name
        raise StopIteration()

    parser = ParserCreate()
    parser.StartElementHandler = start_element

    try:
        parser.Parse(raw, False)
    except StopIteration:
        pass

    # Если документ оказался короче 4096 байт, пробуем дочитать
    if root_tag[0] is None:
        try:
            parser.Parse(b"", True)
        except StopIteration:
            pass

    return root_tag[0] == "FictionBook"


# ---------------------------------------------------------------------------
# Suffix-based detector
# ---------------------------------------------------------------------------


def detect_by_suffix(original_filename: str) -> str | None:
    """Определяет MIME-тип по суффиксу имени файла.

    Сначала проверяет составное расширение .fb2.zip,
    затем ищет суффикс в _SUFFIX_MIME_MAP.

    Returns:
        MIME-тип (строка) или None, если суффикс не распознан.
    """
    name_lower = original_filename.lower()

    # Составное расширение .fb2.zip — обрабатываем до os.path.splitext,
    # чтобы не расколоть на (.fb2, .zip).
    if name_lower.endswith(".fb2.zip"):
        return Mimetype.FB2_ZIP

    _, ext = os.path.splitext(name_lower)
    return _SUFFIX_MIME_MAP.get(ext)


# ---------------------------------------------------------------------------
# Two-phase detect_mime_service
# ---------------------------------------------------------------------------


def detect_mime_service(file, original_filename: str) -> str:
    """Двухфазное определение MIME-типа файла.

    Phase 1 (suffix):  определение по суффиксу имени файла.
    Phase 2A (verify): верификация содержимого под подозреваемый тип.
    Phase 2B (scan):   полный content-based скан (cheapest first).
    Fallback:           suffix-only типы (без content-валидатора)
                        доверяют суффиксу; иначе OCTET_STREAM.

    Args:
        file:             file-like object (BytesIO или raw fd).
        original_filename: имя файла.

    Returns:
        Строка MIME-типа. По умолчанию application/octet-stream.
    """
    logger.info(f"Detecting mimetype of {original_filename}")

    # Phase 1: suffix-based detection
    suspected = detect_by_suffix(original_filename)

    # Есть ли content-валидатор для подозреваемого типа?
    has_content_detector = suspected is not None and any(
        d.mimetype == suspected for d in _CONTENT_DETECTORS
    )

    # Phase 2A: verify suspected type by content
    if suspected is not None and has_content_detector:
        for detector in _CONTENT_DETECTORS:
            if detector.mimetype == suspected:
                if detector.is_valid(file):
                    logger.info(f"Check successful: {original_filename} is {suspected}")
                    return suspected
                # Верификация не прошла → полный скан
                break

    # Phase 2B: full content scan (cheapest first)
    for detector in _CONTENT_DETECTORS:
        if detector.is_valid(file):
            logger.info(f"Check successful: {original_filename} is {detector.mimetype}")
            return detector.mimetype

    # Fallback: suffix-only types (PDF, TXT, etc.) — доверяем суффиксу
    if suspected is not None and not has_content_detector:
        logger.info(f"{original_filename} is {suspected} (suffix-only)")
        return suspected

    logger.info(f"{original_filename} is {Mimetype.OCTET_STREAM}")
    return Mimetype.OCTET_STREAM
