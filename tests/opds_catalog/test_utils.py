from django.test import TestCase

from opds_catalog.utils import get_lang_name, translit


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
