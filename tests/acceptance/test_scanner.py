import os
import zipfile

import pytest
from django.urls import reverse

from opds_catalog.config import catalog_config
from opds_catalog.models import Book, Series, bseries
from opds_catalog.sopdscan import opdsScanner


@pytest.mark.django_db
class TestInpxScanner:
    def test_inpx_serno_parsing(self, tmp_path, catalog):
        """Проверка, что сканер корректно считывает SERNO из INPX файла."""

        # 1. Подготовка структуры INPX
        # Создаем временную папку для библиотеки
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()

        # Чтобы сканер работал, нужно подменить ROOT_LIB в конфиге
        # Мы используем patch, так как catalog_config - это объект
        from unittest.mock import patch

        # Данные для INP файла:
        # Формат по умолчанию: Author, Genre, Title, Series, SerNo, File, Size, LibId, Del, Ext, Date, Lang
        # Разделитель: \x04 (SOPDS standard)
        sep = "\x04"
        inp_content = (
            f"Author{sep}Genre{sep}My Book{sep}My Series{sep}5{sep}book.fb2{sep}1024{sep}1{sep}0{sep}fb2{sep}2023-01-01{sep}ru"
        ).encode("utf-8")

        inp_file_name = "test.inp"
        inpx_file_name = "test.inpx"

        # Создаем ZIP архив, который является INPX файлом
        inpx_path = lib_dir / inpx_file_name
        with zipfile.ZipFile(str(inpx_path), "w") as zf:
            zf.writestr(inp_file_name, inp_content)
            # Добавляем пустой файл книги, чтобы scanner.findbook не ругался, если включены проверки
            zf.writestr("book.fb2", b"dummy content")

        # Также создаем физический файл книги в папке, так как сканер проверяет его наличие
        # (хотя в Inpx.parse есть проверки TEST_ZIP/TEST_FILES, в sopdscan.py используется scanner.findbook)
        book_path = lib_dir / "book.fb2"
        book_path.write_text("dummy")

        # Подменяем настройки через замену свойств в классе SopdsConfig
        from opds_catalog.config import SopdsConfig

        orig_root = SopdsConfig.ROOT_LIB
        orig_inpx_en = SopdsConfig.INPX_ENABLED
        orig_inpx_skip = SopdsConfig.INPX_SKIP_UNCHANGED

        SopdsConfig.ROOT_LIB = property(lambda self: str(lib_dir))
        SopdsConfig.INPX_ENABLED = property(lambda self: True)
        SopdsConfig.INPX_SKIP_UNCHANGED = property(lambda self: False)

        try:
            scanner_obj = opdsScanner()
            scanner_obj.scan_all()
        finally:
            SopdsConfig.ROOT_LIB = orig_root
            SopdsConfig.INPX_ENABLED = orig_inpx_en
            SopdsConfig.INPX_SKIP_UNCHANGED = orig_inpx_skip

        # 2. Проверка результатов
        book = Book.objects.get(title="My Book")
        series = Series.objects.get(ser="My Series")

        # Проверяем связь книги с серией и номер в серии
        # В Django M2M с through-таблицей:
        bs = bseries.objects.get(book=book, ser=series)

        assert bs.ser_no == 5, f"Expected ser_no=5, got {bs.ser_no}"
