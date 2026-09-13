from io import BytesIO
from unittest.mock import MagicMock

import pytest

from book_tools.format.bookfile import BookFile
from book_tools.format.epub import EPub


def test_epub_parse_book_data_handles_nulls():
    """Тест корректной обработки None в parse_book_data метода EPub."""
    # Создаем мок-файл
    file = BytesIO(b"fake epub content")

    # Создаем объект EPub.
    # Чтобы избежать падения в __init__ (который пытается открыть ZIP),
    # мы создадим объект через __new__ и вручную настроим его.
    epub = EPub.__new__(EPub)
    epub.file = file
    epub.original_filename = "test.epub"

    # Имитируем отсутствие всех метаданных
    epub.title = None
    epub.description = None
    epub.authors = None
    epub.tags = None
    epub.series_info = None
    epub.language_code = None
    epub.docdate = None
    epub.issues = None

    # Вызываем тестируемый метод
    result = epub.parse_book_data(file, "test.epub")

    # Проверяем, что результат — это BookFile и в нем нет None там, где должны быть значения по умолчанию
    assert isinstance(result, BookFile)
    assert result.title == "test.epub"  # fallback на original_filename
    assert result.description is None  # description может быть None
    assert result.authors == []  # fallback на пустой список
    assert result.tags == []  # fallback на пустой список
    assert result.series_info is None  # series_info может быть None
    assert result.language_code is None  # language_code может быть None
    assert result.docdate == ""  # fallback на пустую строку
    assert result.issues == []  # fallback на пустой список
