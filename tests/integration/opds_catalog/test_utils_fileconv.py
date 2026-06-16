"""Тесты утилит, требующих БД (FileDataConv, конвертация) — integration."""

import pytest


@pytest.mark.django_db
class TestFileDataConv:
    """Тесты функций конвертации файлов книг (требуют БД)."""

    def test_get_file_data_conv_non_fb2(self, book):
        """Проверка что конвертация не-fb2 возвращает None."""
        from opds_catalog.utils import getFileDataConv

        book.format = "epub"
        result = getFileDataConv(book, "mobi")
        assert result is None

    def test_get_file_data_conv_no_file(self, book):
        """Проверка что getFileDataConv возвращает None при отсутствии файла."""
        from opds_catalog.utils import getFileDataConv

        # Книги с таким файлом не существует на ФС — должен вернуть None
        result = getFileDataConv(book, "epub")
        assert result is None

    def test_get_file_data_conv_unknown_type(self, book):
        """Проверка что неизвестный тип конвертации возвращает None."""
        from opds_catalog.utils import getFileDataConv

        result = getFileDataConv(book, "unknown")
        assert result is None

    def test_get_file_data_epub(self, book):
        """Проверка getFileDataEpub (без файла — None)."""
        from opds_catalog.utils import getFileDataEpub

        result = getFileDataEpub(book)
        assert result is None

    def test_get_file_data_mobi(self, book):
        """Проверка getFileDataMobi (без файла — None)."""
        from opds_catalog.utils import getFileDataMobi

        result = getFileDataMobi(book)
        assert result is None
