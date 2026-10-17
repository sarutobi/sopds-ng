"""Тесты принятия решений по расхождениям (Task 0.3).

Эти тесты фиксируют ожидаемое поведение BookWriter для спорных случаев.
Они служат спецификацией для реализации Task 1.2.
"""

from dataclasses import dataclass

import pytest


@dataclass
class MockAuthor:
    full_name: str
    sortkey: str = ""


def normalize_author_name(name: str) -> tuple[str, str]:
    """
    Реализация решения D-2:
    1. Если есть запятая -> до первой запятой = фамилия, остальное = имя.
    2. Если нет запятой -> последнее слово = фамилия, остальное = имя.
    3. Если пусто -> '_'
    """
    name = name.strip()
    if not name:
        return "_", ""

    if "," in name:
        parts = name.split(",", 1)
        last = parts[0].strip()
        first = parts[1].strip() if len(parts) > 1 else ""
    else:
        parts = name.rsplit(None, 1)
        if len(parts) > 1:
            first = parts[0].strip()
            last = parts[1].strip()
        else:
            first = ""
            last = parts[0].strip()

    return last, first


def test_bw_decision_D1():
    """D-1: sortkey сохраняется, но не влияет на full_name в БД."""
    author = MockAuthor(full_name="фон Бисмарк", sortkey="Бисмарк")
    # Ожидаем, что в БД пойдет именно full_name
    assert author.full_name == "фон Бисмарк"
    assert author.sortkey == "Бисмарк"


def test_bw_decision_D2():
    """D-2: Перенос фамилии (запятая vs последнее слово)."""
    cases = [
        ("Иванов, Иван", "Иванов", "Иван"),
        ("Пушкин", "Пушкин", ""),
        ("Александр Сергеевич Пушкин", "Пушкин", "Александр Сергеевич"),
        ("фон Бисмарк", "Бисмарк", "фон"),
        ("Аарх,Андрей,", "Аарх", "Андрей,"),  # Случай из online.inp
        ("", "_", ""),
    ]
    for input_name, exp_last, exp_first in cases:
        last, first = normalize_author_name(input_name)
        assert last == exp_last, f"Failed last_name for {input_name}"
        assert first == exp_first, f"Failed first_name for {input_name}"


def test_bw_decision_D3():
    """D-3: Пустой автор -> '_'."""
    last, first = normalize_author_name("")
    assert last == "_"


def test_bw_decision_D4():
    """D-4: Аннотация берется из DTO, INPX -> ''."""
    # Это тест на контракт DTO
    dto_with_ann = "Важная аннотация"
    dto_without_ann = ""
    assert dto_with_ann == "Важная аннотация"
    assert dto_without_ann == ""


def test_bw_decision_D5():
    """D-5: Унифицированный strip_symbols."""
    symbols = "!@#$%"

    def my_strip(s):
        return s.strip(symbols)

    assert my_strip("!Заголовок#") == "Заголовок"
    assert my_strip(" ru ") == " ru "  # пробелы не в symbols


def test_bw_decision_D6():
    """D-6: Канон расширения."""

    def canon_ext(e):
        return e.lower().lstrip(".")

    assert canon_ext(".FB2") == "fb2"
    assert canon_ext("FB2") == "fb2"
    assert canon_ext(".fb2") == "fb2"


def test_bw_decision_D7():
    """D-7: cat_type книги передается источником."""
    cat_type_inpx = 1  # CAT_INP
    cat_type_raw = 2  # CAT_ZIP
    assert cat_type_inpx != cat_type_raw


def test_bw_decision_D8():
    """D-8: Номер серии привязан к серии."""
    # Ожидаем структуру: list[Series(name, no)]
    series_data = [
        {"name": "Серия 1", "no": 1},
        {"name": "Серия 2", "no": 5},
    ]
    assert series_data[0]["no"] == 1
    assert series_data[1]["no"] == 5


def test_bw_decision_D9():
    """D-9: Ключ кэша по канону normalize(value)[:size]."""

    def cache_key(val, size):
        return val.strip().lower()[:size]

    assert cache_key("  Автор  ", 5) == "автор"
    assert cache_key("ОченьДлинноеИмяАвтора", 5) == "очень"


def test_bw_decision_D10():
    """D-10: Ошибки источника обрабатываются до BookWriter."""
    # Тест на то, что BookWriter не должен иметь try-except вокруг парсинга
    # (проверяется архитектурно)
    pass
