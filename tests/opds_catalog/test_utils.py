import pytest
import zipfile

from django.test import TestCase

from opds_catalog.utils import get_lang_name, translit, get_infolist_filename


class TestOpdsUtils(TestCase):
    def test_get_lang_name(self) -> None:
        """Проверка преобразования кода языка в его наименование"""
        lang = "ru"
        expected_lang_name = "Russian"
        lang_name = get_lang_name(lang)
        assert lang_name == expected_lang_name

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
        """Проверка удаления символа \n"""
        text = "Это две\nстроки"
        expected_text = "Eto_dve_stroki"
        result_text = translit(text)
        assert result_text == expected_text


@pytest.fixture
def zipped_books_from_fs(wrong_encoded_fb2_zip, zipped_fb2_book_from_fs):
    """Генератор данных для проверки поиска наименования книги в ZIP архиве"""
    return [
        (wrong_encoded_fb2_zip, "Носов - Незнайка-путешественник.fb2", "aaaaa"),
        (zipped_fb2_book_from_fs, "262001.fb2", "262001.fb2"),
        (zipped_fb2_book_from_fs, "262002.fb2", None),
    ]


@pytest.mark.parametrize(
    "book_from_fs, filename, expected",
    [
        ("262001.zip", "262001.fb2", "262001.fb2"),
        ("262001.zip", "262002.fb2", None),
        (
            "wrong_encoded.zip",
            "Носов - Незнайка-путешественник.fb2",
            "ì«ß«ó - ìÑº¡á⌐¬á-»πΓÑΦÑßΓóÑ¡¡¿¬.fb2",
        ),
    ],
    indirect=["book_from_fs"],
)
def test_get_infolist_filename(book_from_fs, filename, expected) -> None:
    """Тест поиска имени файла в zip архиве."""

    with zipfile.ZipFile(book_from_fs) as zip:
        infolist = zip.infolist()
    actual = get_infolist_filename(infolist, filename)
    assert actual == expected
