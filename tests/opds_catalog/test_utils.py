import pytest

from opds_catalog.utils import get_lang_name, translit


class TestOpdsUtils:  # unit
    """Тесты чистых утилитарных функций (без БД, без ФС)."""

    def test_get_lang_name(self) -> None:
        """Проверка преобразования кода языка в его наименование"""
        lang = "ru"
        expected_lang_name = "Russian"
        lang_name = get_lang_name(lang)
        assert lang_name == expected_lang_name

    def test_get_lang_name_unknown(self) -> None:
        """Проверка что неизвестный код возвращается как есть"""
        lang_name = get_lang_name("xx")
        assert lang_name == "xx"

    def test_translit(self) -> None:
        """Проверка утилиты транслитерации"""
        text = "Длинношеий чемодан"
        expected_text = "Dlinnosheij_chemodan"
        result_text = translit(text)
        assert expected_text == result_text

    def test_quotes(self) -> None:
        """Проверка удаления кавычек"""
        text = '"Крейсер «Аврора»"'
        expected_text = "Krejser_Avrora"
        result_text = translit(text)
        assert result_text == expected_text

    def test_remove_newline(self) -> None:
        """Проверка удаления символа \\n"""
        text = "Это две\nстроки"
        expected_text = "Eto_dve_stroki"
        result_text = translit(text)
        assert result_text == expected_text

    def test_to_int_valid(self) -> None:
        """Проверка to_int с валидным значением"""
        from opds_catalog.utils import to_int

        assert to_int("42") == 42
        assert to_int(42) == 42

    def test_to_int_invalid(self) -> None:
        """Проверка to_int с невалидным значением"""
        from opds_catalog.utils import to_int

        assert to_int("abc") == 0
        assert to_int(None) == 0
        assert to_int([1, 2, 3]) == 0

    def test_to_int_custom_default(self) -> None:
        """Проверка to_int с кастомным default"""
        from opds_catalog.utils import to_int

        assert to_int("abc", -1) == -1


@pytest.fixture
def zipped_books_from_fs(wrong_encoded_fb2_zip, zipped_fb2_book_from_fs):
    """Генератор данных для проверки поиска наименования книги в ZIP архиве"""
    return [
        (wrong_encoded_fb2_zip, "Носов - Незнайка-путешественник.fb2", "aaaaa"),
        (zipped_fb2_book_from_fs, "262001.fb2", "262001.fb2"),
        (zipped_fb2_book_from_fs, "262002.fb2", None),
    ]


@pytest.mark.django_db
class TestFileDataConv:  # integration
    """Тесты функций конвертации файлов книг."""

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
