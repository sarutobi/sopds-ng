import zipfile
from io import BytesIO

import pytest
from lxml import etree

from book_tools.format.parsers import EpubParser


def create_minimal_epub(metadata_content: str) -> BytesIO:
    """Создает минимальный валидный EPUB-файл в памяти для тестов."""
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # container.xml
        container_xml = (
            '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
            '<rootfile full-path="OPF/package.opf" />'
            "</container>"
        )
        zf.writestr("META-INF/container.xml", container_xml)

        # opf file
        opf_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<package xmlns="http://www.idpf.org/2007/opf" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'version="2.0">'
            "<metadata>"
            f"{metadata_content}"
            "</metadata>"
            '<manifest><item id="nc" href="content.html" media-type="application/xhtml+xml"/></manifest>'
            '<spine><itemref idref="nc"/></spine>'
            "</package>"
        )
        zf.writestr("OPF/package.opf", opf_xml)
        zf.writestr("OPF/content.html", "<html><body>Test</body></html>")

    buf.seek(0)
    return buf


def test_epub_missing_metadata_fields():
    """Проверяет, что отсутствие обязательных метаданных не вызывает IndexError."""
    # Создаем EPUB без dc:title, dc:language, dc:description
    epub_file = create_minimal_epub("")
    parser = EpubParser(epub_file)
    parser.parse()

    # Эти вызовы должны вернуть значения по умолчанию/None, а не падать с IndexError
    assert parser.title == ""
    assert parser.language_code is None or parser.language_code == ""
    assert parser.description == ""
    assert parser.docdate is None or parser.docdate == ""


def test_epub_partial_metadata():
    """Проверяет работу при частичном наличии метаданных."""
    metadata = "<dc:title>My Book</dc:title>"
    epub_file = create_minimal_epub(metadata)
    parser = EpubParser(epub_file)
    parser.parse()

    assert parser.title == "My Book"
    assert parser.language_code is None or parser.language_code == ""
    assert parser.description == ""
