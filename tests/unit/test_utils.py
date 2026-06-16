"""Тесты чистых утилитарных функций (без БД, без ФС) — unit."""

import pytest

from opds_catalog.utils import get_lang_name, translit


class TestOpdsUtils:
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
        """Проверка удаления символа \n"""
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
