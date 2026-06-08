"""Фикстуры для модуля book_tools."""

from io import BytesIO

import pytest

from book_tools.format.fb2sax import fb2tag
from book_tools.format.parsers import EbookMetaParser, EpubParser
from tests.book_tools.format.helpers import Author, fb2_book_fabric


@pytest.fixture(scope="module")
def epub_parser(get_file_content, epub_book) -> EbookMetaParser:
    """Парсер формата EPub.

    Возвращает экземпляр ``EpubParser`` для реального epub-файла. Позволяет тестировать
    работу парсера EPub без многократного создания.

    :scope: module
    :returns: EpubParser
    :rtype: EbookMetaParser
    """
    return EpubParser(get_file_content(epub_book))


@pytest.fixture(scope="module")
def invalid_epub(get_file_content, zipped_fb2) -> BytesIO:
    """Некорректный тип книги в формате EPub.

    Возвращает содержимое, которое не является корректным epub (на самом деле это ZIP
    с FB2-файлом). Используется для проверки отлова неверного формата.

    :scope: module
    :returns: BytesIO
    :rtype: BytesIO
    """
    return get_file_content(zipped_fb2)


@pytest.fixture
def test_tag() -> fb2tag:
    """Создаёт объект fb2tag с путём (description, title-info, author, first-name).

    Применяется в тестах разбора FB2-тегов.

    :scope: function
    :returns: fb2tag
    :rtype: fb2tag
    """
    # TODO: перенести фикстуру в пакет тестов fb2sax
    return fb2tag(("description", "title-info", "author", "first-name"))


@pytest.fixture
def fb2_params() -> dict:
    """Параметры для построения FB2 книги.

    Возвращает словарь со всеми возможными полями:
    ``title``, ``authors``, ``genres``, ``lang``, ``docdate``, ``annotation``,
    ``series_name``, ``series_no``, ``correct``.
    Тест может переопределить нужные ключи через ``request.getfixturevalue``
    или напрямую изменить возвращаемый словарь.

    :scope: function
    :returns: dict с параметрами
    :rtype: dict
    """
    return {
        "namespace": None,
        "title": "Generated Book",
        "authors": [Author("Pytest", last_name="Genius")],
        "genres": ["genre1"],
        "lang": "ru",
        "docdate": "1970-01-01",
        "annotation": "Test annotation",
        "series_name": "Test series",
        "series_no": 1,
        "correct": True,
    }


@pytest.fixture
def virtual_fb2_book(fb2_params) -> BytesIO:
    """Формирует виртуальную книгу в формате FB2 на основе fb2_params.

    Формирует виртуальную (сгенерированную на лету) FB2-книгу как ``BytesIO``, используя
    значения из ``fb2_params``. Позволяет тестировать парсинг без реальных файлов.

    :scope: function
    :returns: BytesIO с FB2-контентом
    :rtype: BytesIO
    """
    return BytesIO(
        fb2_book_fabric(
            namespace=fb2_params["namespace"],
            title=fb2_params["title"],
            authors=fb2_params["authors"],
            genres=fb2_params["genres"],
            lang=fb2_params["lang"],
            docdate=fb2_params["docdate"],
            series_name=fb2_params["series_name"],
            series_no=fb2_params["series_no"],
            annotation=fb2_params["annotation"],
            correct=fb2_params["correct"],
        )
    )


@pytest.fixture
def create_incorrect_book():
    """Заведомо неверная книга.

    Возвращает ``BytesIO(b"I'm not a fiction book")`` — заведомо неверную книгу.
    Используется для проверки реакций на полностью некорректные входные данные.

    :scope: function
    :returns: BytesIO с некорректным содержимым
    :rtype: BytesIO
    """
    return BytesIO(b"I'm not a fiction book")
