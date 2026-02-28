# Парсеры для разных форматов электронных книг
from lxml.etree import _Element
from typing import Any
import os
import zipfile
from lxml import etree


import base64
from abc import ABC, abstractmethod
from io import BytesIO
from dataclasses import dataclass
from book_tools.format.util import strip_symbols

import logging

from book_tools.exceptions import FB2StructureException
from book_tools.format.fb2sax import fb2parser


@dataclass
class FB2Namespace(object):
    """Возможные пространства имен в xml файле fb2"""

    FICTION_BOOK20: str = "http://www.gribuser.ru/xml/fictionbook/2.0"
    FICTION_BOOK21: str = "http://www.gribuser.ru/xml/fictionbook/2.1"
    XLINK: str = "http://www.w3.org/1999/xlink"


class EbookMetaParser(ABC):
    """Абстрактный класс парсера для электронной книги"""

    ns_map = {"fb": FB2Namespace.FICTION_BOOK20, "l": FB2Namespace.XLINK}

    def __init__(self, file: BytesIO):
        self._file = file

    @abstractmethod
    def extract_cover(self) -> bytes | None:
        """
        Извлечение обложки книги

        Returns:
            bytes: байтовый поток обложки если обложка существует
            None: если обложка не существует

        """
        ...

    @abstractmethod
    def title(self) -> str:
        """Извлечение заголовка книги"""
        ...

    @abstractmethod
    def description(self) -> bytes | None:
        """
        Извлечение аннотации к книге

        Returns:
            bytes: аннотация если есть
            None: если аннотации нет
        """
        ...

    @abstractmethod
    def authors(self) -> list[tuple[str, str]]:
        """
        Извлечение списка авторов книги

        Returns:
            list[tuple[str,str]]: Список авторов в формате (Автор, поисковая строка)
        """
        ...

    @abstractmethod
    def tags(self) -> list[str]:
        """
        Извлечение жанров книги

        Returns:
            list[str]: Список жанров книги
        """
        ...

    @abstractmethod
    def series_info(self) -> dict[str, str]:
        """
        Извлечение информации о серии, в которую входит книга

        Returns:
            dict[str,str]: словарь, в котором содержится информация о названии серии и номер книги в серии
            None: если книга не входит в серию
        """
        ...

    @abstractmethod
    def language_code(self) -> str:
        """
        Извлечение кодя языка книги

        Returns:
            str: код языка
        """
        ...

    @abstractmethod
    def docdate(self) -> str:
        """Извлечение даты формирования книги.

        Returns:
            str: Строковое представление даты формироввания книги

        """
        ...


class FB2(EbookMetaParser):
    """Базовый класс для извлечения метаданных из книг в формате FB2 с помощью lxml."""

    # def __init__(self, file: BytesIO, original_filename: str, mimetype: str):
    def __init__(self, file: BytesIO):
        """Инициализация объекта.

        Автоматически устанавливает параметры
            __namespaces
            _mimetype

        Args:
            file (BytesIO):
                Cодержимое файла книги для парсинга

            original_filename (str):
                Наименовние оригинального файла книги. Если файл размещен в ФС, то это наименование файла в ФС.
                Если файл книги находится в zip архиве, то это наименование файла внутри архива.

            mimetype (str):
                Тип данных MIME для книги. Может быть либо Mimetype.FB2 либо Mimetype.FB2_ZIP

        """
        # Инициализация полей объекта
        super().__init__(file)
        self._etree: etree._ElementTree = None
        self._namespaces: dict[str, str] = {}
        self._log = logging.getLogger(str(self.__class__))
        self.parse()

    def parse(self):
        """Парсинг полученного файла."""
        try:
            self._file.seek(0, 0)
            self._etree = etree.parse(self._file)
        except Exception as e:
            self._log.exception(e)
            raise FB2StructureException(f"The file is not a valid XML: {e}")

        # Установка неймспейсов по содержимому
        if self._etree is not None:
            root = self._etree.getroot()
            for k, v in root.nsmap.items():
                if k is None:
                    self._namespaces["fb"] = v
                if k in ("xlink", "l"):
                    self._namespaces["l"] = v
        else:
            self._log.warning("FB2 file has no namespaces!")

        # Если неймспейсы не были определены, устанавливаем дефолнтные
        if "fb" not in self._namespaces.keys():
            self._namespaces["fb"] = FB2Namespace.FICTION_BOOK20
        if "l" not in self._namespaces.keys():
            self._namespaces["l"] = FB2Namespace.XLINK

    def extract_cover_memory(self):
        return self.extract_cover()

    def extract_cover(self) -> bytes | None:
        """Извлечение обложки книги"""
        try:
            res = self._find_elements_with_namespaces(
                "/fb:FictionBook/fb:description/fb:title-info/fb:coverpage/fb:image"
            )

            if len(res) == 0:
                res = self._find_elements_with_namespaces(
                    "/fb:FictionBook/fb:body//fb:image"
                )

            cover_id: str = res[0].get("{" + FB2Namespace.XLINK + "}href")[1:]

            res = self._find_elements_with_namespaces(
                '/fb:FictionBook/fb:binary[@id="%s"]' % cover_id
            )
            content = base64.b64decode(res[0].text)
            return content
        except Exception as err:
            print("exception Extract %s" % err)
            return None

    def _find_elements(self, xpath: str) -> Any:
        return self._etree.xpath(xpath)

    def _find_elements_with_namespaces(self, xpath: str) -> Any:
        return self._etree.xpath(xpath, namespaces=self._namespaces)

    @property
    def title(self) -> str:
        nodes = self._find_elements_with_namespaces(
            '/fb:FictionBook/fb:description/fb:title-info/fb:book-title|/*[local-name() = "FictionBook"]/*[local-name() = "description"]/*[local-name() = "title-info"]/*[local-name() = "book-title"]',
        )
        if len(nodes) > 0:
            res: str = nodes[0].text.strip()

        return res

    @property
    def description(self) -> bytes | None:
        nodes = self._find_elements_with_namespaces(
            "/fb:FictionBook/fb:description/fb:title-info/fb:annotation|/FictionBook/description/title-info/annotation"
        )
        if len(nodes) > 0:
            return etree.tostring(nodes[0], encoding="utf-8", method="text")

        return None

    @property
    def authors(self) -> list[tuple[str, str]]:
        use_namespaces: bool = True

        def subnode_text(node: etree._ElementTree, name: str) -> str:
            if use_namespaces:
                subnode = node.find("fb:" + name, namespaces=self._namespaces)
            else:
                subnode = node.find(name)
            text = subnode.text if subnode is not None else ""
            return text or ""

        def add_author_from_node(node: etree._ElementTree) -> tuple[str, str]:
            first_name = subnode_text(node, "first-name")
            # middle_name = subnode_text(node, 'middle-name')
            last_name = subnode_text(node, "last-name")
            # self.__add_author__(" ".join([first_name, last_name]), last_name)
            return (" ".join([first_name, last_name]), last_name)

        res = self._find_elements_with_namespaces(
            "/fb:FictionBook/fb:description/fb:title-info/fb:author"
        )
        if len(res) == 0:
            use_namespaces = False
            res = self._find_elements("/FictionBook/description/title-info/author")

        authors: list[tuple[str, str]] = []
        for node in res:
            authors.append(add_author_from_node(node))
        return authors

    @property
    def tags(self) -> list[str]:
        res = self._find_elements_with_namespaces(
            "/fb:FictionBook/fb:description/fb:title-info/fb:genre|/FictionBook/description/title-info/genre"
        )
        tags: list[str] = []
        for node in res:
            tags.append(node.text)
        return tags

    @property
    def series_info(self):
        res = self._find_elements_with_namespaces(
            "/fb:FictionBook/fb:description/fb:title-info/fb:sequence|/FictionBook/description/title-info/sequence"
        )
        if len(res) > 0:
            title = res[0].get("name")
            index = res[0].get("number")

            if title:
                return {"title": title, "index": index}
        return None

    @property
    def language_code(self):
        res = self._find_elements_with_namespaces(
            "/fb:FictionBook/fb:description/fb:title-info/fb:lang|/FictionBook/description/title-info/lang"
        )
        if len(res) > 0:
            return res[0].text
        return None

    @property
    def docdate(self):
        # TODO: оптимизация выдачи результата
        is_attrib = 1
        res = self._find_elements_with_namespaces(
            "/fb:FictionBook/fb:description/fb:document-info/fb:date/@value|/FictionBook/description/document-info/date/@value"
        )
        if len(res) == 0:
            is_attrib = 0
            res = self._find_elements_with_namespaces(
                "/fb:FictionBook/fb:description/fb:document-info/fb:date|/FictionBook/description/document-info/date"
            )
        if len(res) > 0:
            return res[0] if is_attrib else res[0].text

        return None


class FB2sax(EbookMetaParser):
    """
    SAX парсер для книг FB2

    Deprecation warning: парсер объявляется устаревшим в связи
    с реализацией парсера на основе lxml.
    """

    def __init__(self, file, original_filename):
        self._log = logging.getLogger()
        self.fb2parser = fb2parser(1)
        file.seek(0, 0)
        self.fb2parser.parse(file)
        if self.fb2parser.parse_error != 0:
            raise FB2StructureException(
                "FB2sax parse error (%s)" % self.fb2parser.parse_errormsg
            )

    def extract_cover(self):
        if len(self.fb2parser.cover_image.cover_data) > 0:
            try:
                s = self.fb2parser.cover_image.cover_data
                content = base64.b64decode(s)
                return content
            except Exception:
                return None
        return None

    def extract_cover_memory(self):
        return self.extract_cover()

    @property
    def title(self):
        res = ""
        if len(self.fb2parser.book_title.getvalue()) > 0:
            res = self.fb2parser.book_title.getvalue()[0].strip(strip_symbols)
        return res

    @property
    def docdate(self):
        res = self.fb2parser.docdate.getattr("value") or ""
        if len(res) == 0 and len(self.fb2parser.docdate.getvalue()) > 0:
            res = self.fb2parser.docdate.getvalue()[0].strip()
        return res

    @property
    def authors(self):
        for idx, author in enumerate(self.fb2parser.author_last.getvalue()):
            last_name = author.strip(strip_symbols)
            first_name = self.fb2parser.author_first.getvalue()[idx].strip(
                strip_symbols
            )
            yield (" ".join([first_name, last_name]), last_name)

    @property
    def language_code(self):
        res = ""
        if len(self.fb2parser.lang.getvalue()) > 0:
            res = self.fb2parser.lang.getvalue()[0].strip(strip_symbols)
        return res

    @property
    def tags(self):
        for genre in self.fb2parser.genre.getvalue():
            yield genre.lower().strip(strip_symbols)

    @property
    def series_info(self):
        if len(self.fb2parser.series.attrss) > 0:
            s = self.fb2parser.series.attrss[0]
            ser_name = s.get("name")
            if ser_name:
                title = ser_name.strip(strip_symbols)
                index = s.get("number", "0").strip(strip_symbols)

                return {"title": title, "index": index}
        return None

    @property
    def description(self):
        res = ""
        if len(self.fb2parser.annotation.getvalue()) > 0:
            res = "\n".join(self.fb2parser.annotation.getvalue())
            # if len(res) > 0:
            return res
        return None


class EpubParser(EbookMetaParser):
    def __init__(self, file: BytesIO):
        self.file = file
        self.opf_path: str = None  # Путь к основному OPF-файлу
        self.root: _Element = None  # Корневой элемент дерева OPF
        self.nsmap: dict[str, str] = {
            "dc": "http://purl.org/dc/elements/1.1/",
            "opf": "http://www.idpf.org/2007/opf",
        }

    def validate(self) -> bool:
        """
        Проверяет корректность файла EPUB.
        """
        try:
            with zipfile.ZipFile(self.file, mode="r") as zf:
                if "META-INF/container.xml" not in zf.namelist():
                    return False
                return True
        except zipfile.BadZipFile:
            return False

    def _load_opf(self) -> None:
        """
        Читает контейнерный файл и загружает основной OPF-файл.
        """
        with zipfile.ZipFile(self.file, mode="r") as zf:
            container_xml = zf.read("META-INF/container.xml")
            root = etree.fromstring(container_xml)
            rootfile = root.find(
                ".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile"
            )
            if rootfile is not None:
                self.opf_path: str = rootfile.get("full-path")
                opf_xml = zf.read(self.opf_path)
                self.root = etree.fromstring(opf_xml)

    @property
    def title(self) -> str:
        """
        Извлекает название книги.
        """
        title = self._xpath("/opf:package/opf:metadata/dc:title")[0]
        return title.text if title is not None else ""

    @property
    def authors(self) -> list[str]:
        """
        Извлекает список авторов книги.
        """
        creators = self._xpath(
            '/opf:package/opf:metadata/dc:creator[@role="aut"] | /opf:package/opf:metadata/dc:creator[not(@role)]'
        )
        return [creator.text for creator in creators]

    @property
    def tags(self) -> list[str]:
        """
        Извлекает список жанров (тем).
        """
        tags = self._xpath("/opf:package/opf:metadata/dc:subject")
        return [tag.text for tag in tags]

    @property
    def language_code(self) -> str:
        """
        Извлекает язык книги.
        """
        lang = self._xpath("/opf:package/opf:metadata/dc:language")[0]
        return lang.text

    @property
    def series_info(self) -> tuple[str, int] | None:
        """
        Извлекает информацию о серии книги из метаданных EPUB.

        :return: Словарь с названием серии и номером книги в серии, либо None, если информация отсутствует.
        """
        series_node = self._xpath(
            '/opf:package/opf:metadata/opf:meta[@name="calibre:series"]'
        )

        # Если найдено название серии
        if series_node:
            series: str = series_node[0].get("content")
            if series:
                # Пробуем найти индекс серии
                index_node = self._xpath(
                    '/opf:package/opf:metadata/opf:meta[@name="calibre:series_index"]'
                )
                # Если есть название серии и нет индекса в серии, считаем что серия указана ошибочно
                if not index_node:
                    return None
                index: int = int(index_node[0].get("content"))
                return series, index

        return None

    @property
    def docdate(self) -> str | None:
        """
        Возвращает дату документа из метаданных EPUB.

        Если указана дата модификации, возвращается она, иначе первая попавшая дата.
        """
        # Объединяем запросы XPath
        res = self._xpath(
            '/opf:package/opf:metadata/dc:date[@event="modification"] | /opf:package/opf:metadata/dc:date'
        )
        # Возвращаем первую подходящую дату или пустую строку
        return res[0].text if res is not None else ""

    @property
    def description(self) -> str:
        """
        Извлекает описание книги (аннотацию).
        """
        desc = self._xpath("/opf:package/opf:metadata/dc:description")[0]
        return desc.text.strip() if desc is not None else ""

    def extract_cover(self) -> bytes | None:
        """
        Извлекает обложку книги из файла EPUB.

        Возвращает байтовый объект с изображением обложки или None, если обложка не найдена.

        Эта функция пытается найти ссылку на обложку в метаинформации файла EPUB. Если обложка указана,
        она извлекается из соответствующего ресурса, указанного в манифесте.

        Параметры:
            Нет (метод использует состояние текущего объекта)

        Возвращаемое значение:
            bytes | None: Байты изображения обложки или None, если обложка отсутствует.
        """

        # Запросы для получения обложки
        cover_queries: list[str] = [
            '/opf:package/opf:manifest/opf:item[@properties="cover-image"]',
            '/opf:package/opf:metadata/opf:meta[@name="cover"]',
            '/opf:package/opf:metadata/meta[@name="cover"]',
            '/package/metadata/meta[@name="cover"]',
            '/opf:package/opf:guide/opf:reference[@type="other.ms-coverimage-standard"][@title="Cover"]',
            '/opf:package/opf:guide/opf:reference[@type="other.ms-coverimage-standard"]',
            '/opf:package/opf:manifest/opf:item[@id="cover"]',
        ]
        # Пытаемся найти ссылку на обложку
        for query in cover_queries:
            try:
                node = self._xpath(query)[0]
                property: str = node.get("content")

                # Непосредственно находим обложку по ID с помощью XPath
                cover_item = self._xpath(f".//opf:item[@id='{property}']")[0]

                # Получаем ссылку на обложку и считываем содержимое файла
                href = cover_item.get("href")
                opf_dir = os.path.dirname(self.opf_path)
                with zipfile.ZipFile(self.file, mode="r") as zf:
                    return zf.read(os.path.join(opf_dir, href))
                break
            except (IndexError, AttributeError):
                continue
        return None

    def parse(self) -> None:
        """
        Запускает процесс парсинга и возвращает собранные данные.
        """
        if not self.validate():
            raise ValueError("Некорректный файл EPUB.")

        self._load_opf()
        if self.root is None:
            raise ValueError("Не удалось загрузить OPF-файл.")

    def _xpath(self, query: str):
        """Поиск узла дерева по запросу"""
        res = self.root.xpath(query, namespaces=self.nsmap)
        return res
