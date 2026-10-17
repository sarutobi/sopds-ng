import os
import zipfile
from io import BytesIO

import pytest

from book_tools.format import create_bookfile


def test_too_large_file():
    """Тест на попытку прочитать файл, размер которого превышает лимит."""
    # Создаем "огромный" файл (в памяти для теста, но имитируем путь)
    # На практике мы хотим, чтобы система даже не пыталась сделать .read(), если размер файла на диске слишком велик.
    # Для этого теста создадим временный файл большого размера.
    with open("huge_file.fb2", "wb") as f:
        # 101 MB (если лимит будет 100 MB)
        f.seek(101 * 1024 * 1024)
        f.write(b"\0")

    try:
        # Ожидаем, что система выбросит исключение или вернет ошибку,
        # вместо того чтобы попытаться прочитать все 100МБ в RAM.
        with pytest.raises(ValueError, match="File size exceeds maximum limit"):
            create_bookfile("huge_file.fb2")
    finally:
        if os.path.exists("huge_file.fb2"):
            os.remove("huge_file.fb2")


def test_zip_bomb():
    """Тест на zip-бомбу (высокий коэффициент сжатия)."""
    # Чтобы детектор MIME определил файл как FB2_ZIP, внутри должен быть файл,
    # который выглядит как FB2 (хотя бы иметь XML структуру)
    bomb_content = (
        b'<?xml version="1.0"?><FictionBook><title>Bomb</title></FictionBook>'
    )
    # Создаем очень большое содержимое, которое отлично сжимается
    large_data = bomb_content + b"\0" * (100 * 1024 * 1024)

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.writestr("book.fb2", large_data)

    zip_buffer.seek(0)

    try:
        with pytest.raises(
            ValueError,
            match="Compression ratio too high|File size exceeds|Uncompressed file size exceeds",
        ):
            create_bookfile(zip_buffer, "bomb.zip")
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")


def test_too_many_files_in_zip():
    """Тест на архив с огромным количеством файлов."""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zf:
        for i in range(10001):  # Если лимит 10000
            zf.writestr(f"file_{i}.fb2", b"small content")

    zip_buffer.seek(0)

    try:
        with pytest.raises(ValueError, match="Too many files in archive"):
            create_bookfile(zip_buffer, "many_files.zip")
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")
