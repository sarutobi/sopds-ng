"""Тесты извлечения информации о серии из FB2 с некорректными тегами <sequence>."""

import io

from book_tools.format.parsers import FB2

FB2_NS = "http://www.gribuser.ru/xml/fictionbook/2.0"


def _make_fb2(sequence_attrs: dict[str, str] | None) -> bytes:
    """Создаёт минимальный FB2 с тегом <sequence> с заданными атрибутами."""
    attrs = " ".join(f'{k}="{v}"' for k, v in (sequence_attrs or {}).items())
    seq = f"<sequence {attrs}/>" if attrs else "<sequence/>"
    return (
        f'<?xml version="1.0" encoding="utf-8"?>'
        f'<FictionBook xmlns="{FB2_NS}">'
        f"<description><title-info>"
        f"<book-title>Test Book</book-title>"
        f"{seq}"
        f"</title-info></description>"
        f"<body><section><p>text</p></section></body>"
        f"</FictionBook>"
    ).encode("utf-8")


def test_sequence_without_name_attribute() -> None:
    """Тег <sequence number="1"/> без атрибута name не должен давать series_info."""
    parser = FB2(io.BytesIO(_make_fb2({"number": "1"})))
    assert parser.series_info is None


def test_sequence_with_empty_name() -> None:
    """Пустой атрибут name эквивалентен отсутствию серии."""
    parser = FB2(io.BytesIO(_make_fb2({"name": "", "number": "1"})))
    assert parser.series_info is None


def test_sequence_with_name() -> None:
    """Корректный тег <sequence name="..." number="..."/> возвращает серию."""
    parser = FB2(io.BytesIO(_make_fb2({"name": "My Series", "number": "3"})))
    assert parser.series_info == {"title": "My Series", "index": "3"}


def test_sequence_without_attributes() -> None:
    """Тег <sequence/> без атрибутов не должен давать series_info."""
    parser = FB2(io.BytesIO(_make_fb2(None)))
    assert parser.series_info is None
