# Парсеры для разных форматов электронных книг
import base64
import logging
import os
import zipfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Optional

from lxml import etree
from lxml.etree import _Element

from book_tools.exceptions import FB2StructureException
from book_tools.format.util import strip_symbols

logger = logging.getLogger(__name__)


@dataclass
class FB2Namespace(object):
    """Возможные пространства имен в xml файле fb2"""

    FICTION_BOOK20: str = "http://www.gribuser.ru/xml/fictionbook/2.0"
    FICTION_BOOK21: str = "http://www.gribuser.ru/xml/fictionbook/2.1"
    XLINK: str = "http://www.w3.org/1999/xlink"


class EbookMetaParser(ABC):
    """Абстрактный класс парсера для электронной книги."""

    ns_map = {"fb": FB2Namespace.FICTION_BOOK20, "l": FB2Namespace.XLINK}

    def __init__(self, file: BytesIO):
        self._file = file

    @abstractmethod
    def extract_cover(self) -> bytes | None:
        """Извлечение обложки книги.

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
        self._etree: Optional[etree._ElementTree] = None
        self._namespaces: dict[str, str] = {}
        self._log = logging.getLogger(str(self.__class__))
        self._metadata_cache: dict[str, Any] = {}
        self.parse()

    def parse(self):
        """Парсинг полученного файла."""
        self._etree = None
        self._metadata_cache = {}
        try:
            self._file.seek(0, 0)
            data = self._file.read()
            parser = etree.XMLParser(
                resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False
            )
            self._etree = etree.parse(BytesIO(data), parser=parser)

            self._extract_metadata_via_xpath()
        except etree.XMLSyntaxError:
            try:
                self._file.seek(0, 0)
                data = self._file.read()
                decoded_data = data.decode("cp1251").encode("utf-8")
                parser = etree.XMLParser(
                    resolve_entities=False,
                    no_network=True,
                    load_dtd=False,
                    huge_tree=False,
                )
                self._etree = etree.parse(BytesIO(decoded_data), parser=parser)
                self._extract_metadata_via_xpath()
            except Exception as e:
                self._log.exception(e)
                raise FB2StructureException(f"The file is not a valid XML: {e}")
        except Exception as e:
            self._log.exception(e)
            raise FB2StructureException(f"The file is not a valid XML: {e}")

    def _extract_metadata_via_xpath(self):
        root = self._etree.getroot()

        # Неймспейсы
        for k, v in root.nsmap.items():
            if k is None:
                self._namespaces["fb"] = v
            if k in ("xlink", "l"):
                self._namespaces["l"] = v

        if "fb" not in self._namespaces:
            self._namespaces["fb"] = FB2Namespace.FICTION_BOOK20
        if "l" not in self._namespaces:
            self._namespaces["l"] = FB2Namespace.XLINK

        # Метаданные
        title_node = root.xpath(
            ".//fb:description/fb:title-info/fb:book-title", namespaces=self._namespaces
        )
        if title_node:
            self._metadata_cache["title"] = (title_node[0].text or "").strip()

        authors_nodes = root.xpath(
            ".//fb:description/fb:title-info/fb:author", namespaces=self._namespaces
        )
        authors = []
        for node in authors_nodes:
            first = node.find("fb:first-name", namespaces=self._namespaces)
            last = node.find("fb:last-name", namespaces=self._namespaces)
            f_text = first.text if first is not None else ""
            l_text = last.text if last is not None else ""
            authors.append((f"{f_text or ''} {l_text or ''}".strip(), l_text or ""))
        self._metadata_cache["authors"] = authors

        genres_nodes = root.xpath(
            ".//fb:description/fb:title-info/fb:genre", namespaces=self._namespaces
        )
        self._metadata_cache["tags"] = [node.text or "" for node in genres_nodes]

        seq_node = root.xpath(
            ".//fb:description/fb:title-info/fb:sequence", namespaces=self._namespaces
        )
        if seq_node:
            self._metadata_cache["series_info"] = {
                "title": seq_node[0].get("name"),
                "index": seq_node[0].get("number"),
            }

        lang_node = root.xpath(
            ".//fb:description/fb:title-info/fb:lang", namespaces=self._namespaces
        )
        if lang_node:
            self._metadata_cache["language_code"] = lang_node[0].text or ""

        # Исправленный сбор даты: ищем все узлы date, берем первый с непустым значением
        date_nodes = root.xpath(
            ".//fb:description/fb:title-info/fb:date | .//fb:description/fb:document-info/fb:date",
            namespaces=self._namespaces,
        )
        docdate = None
        for node in date_nodes:
            val = node.get("value") or node.text
            if val and val.strip():
                docdate = val.strip()
                break
        if docdate:
            self._metadata_cache["docdate"] = docdate

        anno_node = root.xpath(
            ".//fb:description/fb:annotation | .//fb:description/fb:title-info/fb:annotation",
            namespaces=self._namespaces,
        )
        if anno_node:
            self._metadata_cache["description_elem"] = anno_node[0]

        # Исправленная обложка: приоритет coverpage -> любое изображение
        cover_img_node = root.xpath(
            ".//fb:description/fb:coverpage/fb:image", namespaces=self._namespaces
        )
        if not cover_img_node:
            cover_img_node = root.xpath(".//fb:image", namespaces=self._namespaces)

        if cover_img_node:
            node = cover_img_node[0]
            # Пробуем извлечь href с учетом пространства имен xlink
            href = node.get("{" + FB2Namespace.XLINK + "}href") or node.get("href")
            if href:
                cover_id = href.lstrip("#")
                binary_node = root.xpath(
                    f'.//fb:binary[@id="{cover_id}"]', namespaces=self._namespaces
                )
                if binary_node and binary_node[0].text:
                    try:
                        self._metadata_cache["cover"] = base64.b64decode(
                            binary_node[0].text.strip()
                        )
                    except Exception:
                        pass
            elif not cover_img_node[0].get("href"):
                # Если coverpage нет, но есть одиночный binary, который может быть обложкой
                # (зависит от требований тестов, обычно binary-based)
                pass

    def extract_cover_memory(self):
        return self.extract_cover()

    def extract_cover(self) -> bytes | None:
        """Извлечение обложки книги."""
        return self._metadata_cache.get("cover")

    def _find_elements(self, xpath: str) -> Any:
        return self._etree.xpath(xpath)

    def _find_elements_with_namespaces(self, xpath: str) -> Any:
        return self._etree.xpath(xpath, namespaces=self._namespaces)

    @property
    def title(self) -> str:
        return self._metadata_cache.get("title", "")

    @property
    def description(self) -> bytes | None:
        elem = self._metadata_cache.get("description_elem")
        if elem is not None:
            return etree.tostring(elem, encoding="utf-8", method="text")
        return None

    @property
    def authors(self) -> list[tuple[str, str]]:
        return self._metadata_cache.get("authors", [])

    @property
    def tags(self) -> list[str]:
        return self._metadata_cache.get("tags", [])

    @property
    def series_info(self):
        return self._metadata_cache.get("series_info")

    @property
    def language_code(self):
        return self._metadata_cache.get("language_code")

    @property
    def docdate(self):
        return self._metadata_cache.get("docdate")


class EpubParser(EbookMetaParser):
    def __init__(self, file: BytesIO):
        self.file = file
        self.opf_path: str  # Путь к основному OPF-файлу
        self.root: _Element  # Корневой элемент дерева OPF
        self.nsmap: dict[str, str] = {
            "dc": "http://purl.org/dc/elements/1.1/",
            "opf": "http://www.idpf.org/2007/opf",
        }

    def validate(self) -> bool:
        """Проверяет корректность файла EPUB."""
        try:
            with zipfile.ZipFile(self.file, mode="r") as zf:
                if "META-INF/container.xml" not in zf.namelist():
                    return False
                return True
        except zipfile.BadZipFile:
            return False

    def _load_opf(self) -> None:
        """Читает контейнерный файл и загружает основной OPF-файл."""
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
        """Извлекает название книги."""
        title = self._xpath("/opf:package/opf:metadata/dc:title")[0]
        return title.text if title is not None else ""

    @property
    def authors(self) -> list[str]:
        """Извлекает список авторов книги."""
        creators = self._xpath(
            '/opf:package/opf:metadata/dc:creator[@role="aut"] | /opf:package/opf:metadata/dc:creator[not(@role)]'
        )
        return [creator.text for creator in creators]

    @property
    def tags(self) -> list[str]:
        """Извлекает список жанров (тем)."""
        tags = self._xpath("/opf:package/opf:metadata/dc:subject")
        return [tag.text for tag in tags]

    @property
    def language_code(self) -> str:
        """Извлекает язык книги."""
        lang = self._xpath("/opf:package/opf:metadata/dc:language")[0]
        return lang.text

    @property
    def series_info(self) -> tuple[str, int] | None:
        """Извлекает информацию о серии книги из метаданных EPUB.

        :return: Словарь с названием серии и номером книги в серии, либо None,
        если информация отсутствует.
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
                # Если есть название серии и нет индекса в серии, считаем что серия
                # указана ошибочно
                if not index_node:
                    return None
                index: int = int(index_node[0].get("content"))
                return series, index

        return None

    @property
    def docdate(self) -> str | None:
        """Возвращает дату документа из метаданных EPUB.

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
        """Извлекает описание книги (аннотацию)."""
        desc = self._xpath("/opf:package/opf:metadata/dc:description")[0]
        return desc.text.strip() if desc is not None else ""

    def extract_cover(self) -> bytes | None:
        """Извлекает обложку книги из файла EPUB.

        Возвращает байтовый объект с изображением обложки или None, если обложка
        не найдена.

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
        """Запускает процесс парсинга и возвращает собранные данные."""
        if not self.validate():
            raise ValueError("Некорректный файл EPUB.")

        self._load_opf()
        if self.root is None:
            raise ValueError("Не удалось загрузить OPF-файл.")

    def _xpath(self, query: str):
        """Поиск узла дерева по запро запросу."""
        res = self.root.xpath(query, namespaces=self.nsmap)
        return res
