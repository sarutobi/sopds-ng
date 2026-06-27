import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class Author:
    """Объект Автор для включения в состав книги.

    Атрибуты:
        first_name: Имя автора
        middle_name: Среднее имя (отчество)
        last_name: Фамилия автора
    """

    first_name: str | None = None
    middle_name: str | None = None
    last_name: str = ""


def fb2_book_fabric(
    title: str | None = None,
    authors: list[Author] | None = None,
    namespace: str | None = None,
    **kwargs,
) -> bytes:
    """Создаёт минимальный FB2-файл для тестов.

    Параметры:
        title: заголовок книги (если не указан, элемент <book-title> будет пустым)
        authors: список авторов (если не указан, элемент <author> не создаётся)
        namespace: пространство имён (по умолчанию FictionBook 2.0)

    Возвращает:
        байтовое представление XML-документа в кодировке UTF-8
    """
    ns = namespace or "http://www.gribuser.ru/xml/fictionbook/2.0"
    root = ET.Element("FictionBook", attrib={"xmlns": ns})

    description = ET.SubElement(root, "description")
    title_info = ET.SubElement(description, "title-info")

    # book-title
    book_title = ET.SubElement(title_info, "book-title")
    if title:
        book_title.text = title

    # authors
    if authors:
        for author in authors:
            author_el = ET.SubElement(title_info, "author")
            if author.first_name:
                first_name_el = ET.SubElement(author_el, "first-name")
                first_name_el.text = author.first_name
            if author.middle_name:
                middle_name_el = ET.SubElement(author_el, "middle-name")
                middle_name_el.text = author.middle_name
            if author.last_name:
                last_name_el = ET.SubElement(author_el, "last-name")
                last_name_el.text = author.last_name

    return b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(
        root, encoding="utf-8"
    )
