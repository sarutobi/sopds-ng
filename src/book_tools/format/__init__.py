import logging
import os
from io import BytesIO

from book_tools.format.bookfile import BookFile
from book_tools.format.mimetype import Mimetype as Mimetype
from book_tools.format.util import list_zip_file_infos as list_zip_file_infos
from book_tools.mime_detector import detect_mime_service as detect_mime_service
from book_tools.services import create_bookfile_service

logger = logging.getLogger(__name__)

# Лимиты для предотвращения DoS (SEC-07)
MAX_BOOK_SIZE = 100 * 1024 * 1024  # 100 MB


def create_bookfile(path, original_filename=None) -> BookFile:
    """Извлечение метаданных электронной книги.

    Args:
        path: Путь к файлу (строка) или file-like объект (BytesIO).
        original_filename: Имя файла (обязательно если path — file-like).

    Returns:
        BookFile: извлеченные метаданные книги.
    """
    if isinstance(path, str):
        # If path is a string, open fd and pass raw (без BytesIO)
        if original_filename is None:
            original_filename = os.path.basename(path)

        # Проверка размера файла на диске перед чтением (SEC-07)
        if os.path.getsize(path) > MAX_BOOK_SIZE:
            raise ValueError(f"File size exceeds maximum limit ({MAX_BOOK_SIZE} bytes)")

        logger.info(f"Read {original_filename} content from file system")
        fd = open(path, "rb")
        try:
            return create_bookfile_service(BytesIO(fd.read()), original_filename)
        finally:
            fd.close()
    else:
        # File-like object (BytesIO) — pass through directly
        if original_filename is None:
            raise ValueError("original_filename is required for file-like objects")

        # Проверка размера переданного объекта (SEC-07)
        # Пытаемся определить размер без полного чтения в память
        if hasattr(path, "getbuffer"):
            size = path.getbuffer().nbytes
        else:
            # Фоллбэк для обычных BytesIO/io.BufferedReader
            current_pos = path.tell()
            path.seek(0, os.SEEK_END)
            size = path.tell()
            path.seek(current_pos)

        if size > MAX_BOOK_SIZE:
            raise ValueError(f"File size exceeds maximum limit ({MAX_BOOK_SIZE} bytes)")

        data = BytesIO(path.read())
        return create_bookfile_service(data, original_filename)
