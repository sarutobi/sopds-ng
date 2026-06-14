"""Фикстуры для модуля book_tools."""

from io import BytesIO
from types import MappingProxyType

import pytest

from book_tools.format.fb2sax import fb2tag
from book_tools.format.parsers import EbookMetaParser, EpubParser
from tests.book_tools.format.helpers import Author, fb2_book_fabric

# ---------------------------------------------------------------------------
# Конфигурация FB2-книги по умолчанию (immutable)
# ---------------------------------------------------------------------------

_DEFAULT_FB2_PARAMS = MappingProxyType(
    {
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
)


def build_fb2_book(**overrides) -> BytesIO:
    """Создаёт виртуальную FB2-книгу как BytesIO.

    Принимает любые переопределяемые параметры (title, authors, lang, ...).
    Параметры, не указанные в ``overrides``, берутся из набора по умолчанию.

    Пример::

        build_fb2_book(title="Custom", lang="en")

    :returns: BytesIO с FB2-контентом
    :rtype: BytesIO
    """
    params = dict(_DEFAULT_FB2_PARAMS)
    params.update(overrides)
    return BytesIO(
        fb2_book_fabric(
            namespace=params["namespace"],
            title=params["title"],
            authors=params["authors"],
            genres=params["genres"],
            lang=params["lang"],
            docdate=params["docdate"],
            series_name=params["series_name"],
            series_no=params["series_no"],
            annotation=params["annotation"],
            correct=params["correct"],
        )
    )


# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------


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
def fb2_params() -> MappingProxyType:
    """Параметры для построения FB2 книги (immutable).

    Возвращает ``MappingProxyType`` (неизменяемое dict-подобное представление)
    со всеми полями по умолчанию: ``title``, ``authors``, ``genres``, ``lang``,
    ``docdate``, ``annotation``, ``series_name``, ``series_no``, ``correct``.

    Для создания книги с кастомными параметрами используйте ``build_fb2_book()``
    напрямую или переопределите фикстуру в своём conftest.py.

    :returns: MappingProxyType
    :rtype: MappingProxyType
    """
    return _DEFAULT_FB2_PARAMS


@pytest.fixture
def virtual_fb2_book() -> BytesIO:
    """Формирует виртуальную книгу в формате FB2 как BytesIO.

    Использует стандартные параметры из ``_DEFAULT_FB2_PARAMS``.
    Для кастомных параметров вызовите ``build_fb2_book()`` напрямую в тесте.

    :scope: function
    :returns: BytesIO с FB2-контентом
    :rtype: BytesIO
    """
    return build_fb2_book()


@pytest.fixture
def create_incorrect_book() -> BytesIO:
    """Заведомо неверная книга.

    Возвращает ``BytesIO(b"I'm not a fiction book")`` — заведомо неверную книгу.
    Используется для проверки реакций на полностью некорректные входные данные.

    :scope: function
    :returns: BytesIO с некорректным содержимым
    :rtype: BytesIO
    """
    return BytesIO(b"I'm not a fiction book")
