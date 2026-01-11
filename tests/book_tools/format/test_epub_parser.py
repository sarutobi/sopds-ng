from book_tools.format.parsers import EbookMetaParser, EpubParser

# from tests.conftest import epub_book_from_fs
import pytest
import os

from book_tools.format.epub import EPub, EPub_new
from tests.opds_catalog.helpers import read_file_as_iobytes


@pytest.mark.parametrize(
    "book",
    [
        "mirer.epub",
    ],
)
def test_epub_parser(test_rootlib, book) -> None:
    file = read_file_as_iobytes(os.path.join(test_rootlib, book))
    book_actual = EPub(file, "Test Book")
    book_new = EPub_new(file, "Test Book").parse_book_data(file, "Test Book")
    assert book_actual == book_new


@pytest.fixture(scope="module")
def parsed_epub(epub_parser) -> EbookMetaParser:
    epub_parser.parse()
    return epub_parser


class TestEpubParserValidation:
    """тесты валидации книги парсером epub"""

    def test_valid_epub(self, epub_parser) -> None:
        assert epub_parser.validate()

    def test_invalid_epub(self, invalid_epub) -> None:
        parser = EpubParser(invalid_epub)
        assert not parser.validate()


class TestEpubParserValues(object):
    """Тесты извлечения данных книги парсером epub"""

    def test_title(self, parsed_epub) -> None:
        """Тест извлечения заголовка"""
        expected = "У меня девять жизней (шф (продолжатели))"
        assert parsed_epub.title == expected

    def test_authors(self, parsed_epub) -> None:
        """Тест извлечения авторов"""
        expected = [
            "Александр  Мирер",
        ]
        assert parsed_epub.authors == expected

    def test_tags(self, parsed_epub) -> None:
        """Тест извлечения жанров"""
        expected = [
            "sf",
        ]
        assert parsed_epub.tags == expected

    def test_language_code(self, parsed_epub) -> None:
        """Тест извлечения кода языка"""
        expected = "ru"
        assert parsed_epub.language_code == expected

    def test_series_info(self, parsed_epub) -> None:
        """Тест извлечения информации о книжной серии"""
        expected = None
        assert parsed_epub.series_info == expected

    def test_docdate(self, parsed_epub) -> None:
        """Тест извлечения информации о дате публикации"""
        expected = "2015"
        assert parsed_epub.docdate == expected

    def test_description(self, parsed_epub) -> None:
        """Тест извлечения аннотации к книге"""
        expected = 28
        assert len(parsed_epub.description) == expected

    def test_cover(self, parsed_epub) -> None:
        """Тест извлечения аннотации к книге"""
        expected = 41886
        assert len(parsed_epub.extract_cover()) == expected
