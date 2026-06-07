"""Тесты для сервисов opds_catalog."""

import pytest
import zipfile
from opds_catalog.services import extract_fb2_cover, unzip_fb2_service
from book_tools.exceptions import FB2StructureException


@pytest.mark.django_db
@pytest.mark.parametrize(
    "book_from_fs, expected", [("simple_fb2", 56360)], indirect=["book_from_fs"]
)
def test_extract_fb2_cover_service(book_from_fs, expected) -> None:
    """Тест получения обложки из книги fb2."""
    cover = extract_fb2_cover(book_from_fs, "", "")
    assert cover is not None
    assert len(cover) == expected


@pytest.mark.parametrize(
    "f_data, f_expected",
    [
        ("fb2_book_from_fs", "fb2_book_from_fs"),
        ("zipped_fb2_book_from_fs", "fb2_book_from_fs"),
    ],
)
def test_unzip_fb2_service(f_data, f_expected, request) -> None:
    """Тест сервиса распаковки файла."""
    data = request.getfixturevalue(f_data)
    expected = request.getfixturevalue(f_expected)
    actual = unzip_fb2_service(data)
    assert actual.getvalue() == expected.getvalue()


@pytest.mark.django_db
def test_extract_fb2_cover_no_cover(fb2_without_cover) -> None:
    """Тест получения обложки из fb2 файла без обложки."""
    cover = extract_fb2_cover(fb2_without_cover, "", "")
    assert cover is None


@pytest.mark.django_db
def test_extract_fb2_cover_invalid(invalid_fb2) -> None:
    """Тест получения обложки из некорректного fb2 файла."""
    # Парсер вызывает FB2StructureException при некорректном XML
    with pytest.raises(FB2StructureException):
        extract_fb2_cover(invalid_fb2, "", "")


@pytest.mark.django_db
def test_unzip_fb2_not_a_zip(not_a_zip_file) -> None:
    """Тест обработки данных, которые is_zipfile() не распознает как ZIP архив."""
    # Для фикстуры not_a_zip_file is_zipfile() возвращает False
    # Функция должна вернуть оригинальный поток без исключения
    from io import BytesIO

    result = unzip_fb2_service(not_a_zip_file)
    assert isinstance(result, BytesIO)
    assert result is not None


@pytest.mark.django_db
def test_unzip_fb2_corrupted_valid_header(corrupted_zip_valid_header) -> None:
    """Тест обработки поврежденного zip архива, который is_zipfile() распознает как ZIP."""
    # Для фикстуры corrupted_zip_valid_header is_zipfile() возвращает True
    # При попытке открыть архив zipfile.ZipFile() вызовет BadZipFile из-за поврежденной структуры
    with pytest.raises(zipfile.BadZipFile):
        unzip_fb2_service(corrupted_zip_valid_header)


@pytest.mark.django_db
def test_unzip_fb2_multiple_files(zip_with_multiple_files) -> None:
    """Тест обработки ZIP архива с несколькими файлами."""
    # Функция должна вызвать исключение с сообщением "Archive contains more than 1 files!"
    with pytest.raises(Exception, match="Archive contains more than 1 files!"):
        unzip_fb2_service(zip_with_multiple_files)


@pytest.mark.django_db
def test_unzip_fb2_empty_zip(empty_zip) -> None:
    """Тест обработки пустого ZIP архива."""
    # Пустой архив вызывает IndexError при попытке z.namelist()[0]
    with pytest.raises(IndexError):
        unzip_fb2_service(empty_zip)


@pytest.mark.django_db
def test_unzip_fb2_corrupted_file_content(zip_with_corrupted_file_content) -> None:
    """Тест обработки ZIP архива с поврежденным содержимым файла."""
    # Архив должен открыться, но при чтении файла может возникнуть ошибка
    # В текущей реализации функция читает файл через z.open()
    # Если данные повреждены, может возникнуть BadZipFile или другие ошибки
    # Проверяем, что функция вызывает исключение при чтении
    with pytest.raises(Exception):
        unzip_fb2_service(zip_with_corrupted_file_content)


@pytest.mark.django_db
def test_unzip_fb2_non_fb2(zip_with_non_fb2) -> None:
    """Тест обработки zip архива с не fb2 файлом."""
    result = unzip_fb2_service(zip_with_non_fb2)
    # Ожидается, что функция вернет содержимое архива (не fb2)
    # или обработает его как обычный файл
    assert result is not None
