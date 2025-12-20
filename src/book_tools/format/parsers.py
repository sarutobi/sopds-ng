# Парсеры для разных форматов электронных книг
from typing import Any
import os
from urllib.parse import unquote
import zipfile
from lxml import etree

from book_tools.format.bookfile import BookFile
from book_tools.format.mimetype import Mimetype

import base64
from abc import ABC, abstractmethod
from io import BytesIO
from dataclasses import dataclass
from book_tools.format.util import strip_symbols

import logging

from book_tools.exceptions import FB2StructureException, EpubStructureException
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
    def extract_cover(self) -> bytes | None: ...

    @abstractmethod
    def title(self) -> str: ...

    @abstractmethod
    def description(self) -> bytes | None: ...

    @abstractmethod
    def authors(self) -> list[tuple[str, str]]: ...

    @abstractmethod
    def tags(self) -> list[str]: ...

    @abstractmethod
    def series_info(self) -> dict[str, str]: ...

    @abstractmethod
    def language_code(self) -> str: ...

    @abstractmethod
    def docdate(self) -> str: ...


class FB2(EbookMetaParser):
    """Базовый класс для извлечения метаданных из книг в формате FB2 с помощью lxml"""

    def __init__(self, file: BytesIO, original_filename: str, mimetype: str):
        """
        Инициализация объекта. Автоматически устанавливает параметры
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
        """Парсинг полученного файла"""
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
            "/fb:FictionBook/fb:description/fb:title-info/fb:book-title",
        )
        if len(nodes) == 0:
            nodes = self._find_elements(
                '/*[local-name() = "FictionBook"]/*[local-name() = "description"]/*[local-name() = "title-info"]/*[local-name() = "book-title"]'
            )
        if len(nodes) > 0:
            res: str = nodes[0].text

        return res

    @property
    def description(self) -> bytes | None:
        nodes = self._find_elements_with_namespaces(
            "/fb:FictionBook/fb:description/fb:title-info/fb:annotation"
        )
        if len(nodes) == 0:
            nodes = self._find_elements(
                "/FictionBook/description/title-info/annotation"
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
            "/fb:FictionBook/fb:description/fb:title-info/fb:genre"
        )
        if len(res) == 0:
            res = self._find_elements("/FictionBook/description/title-info/genre")
        tags: list[str] = []
        for node in res:
            tags.append(node.text)
        return tags

    @property
    def series_info(self):
        res = self._find_elements_with_namespaces(
            "/fb:FictionBook/fb:description/fb:title-info/fb:sequence"
        )
        if len(res) == 0:
            res = self._find_elements("/FictionBook/description/title-info/sequence")
        if len(res) > 0:
            title = res[0].get("name")
            index = res[0].get("number")

            if title:
                return {"title": title, "index": index}
        return None

    @property
    def language_code(self):
        res = self._find_elements_with_namespaces(
            "/fb:FictionBook/fb:description/fb:title-info/fb:lang"
        )
        if len(res) == 0:
            res = self._find_elements("/FictionBook/description/title-info/lang")
        if len(res) > 0:
            return res[0].text
        return None

    @property
    def docdate(self):
        # TODO: оптимизация выдачи результата
        is_attrib: int = 1
        res = self._find_elements_with_namespaces(
            "/fb:FictionBook/fb:description/fb:document-info/fb:date/@value"
        )
        if len(res) == 0:
            res = self._find_elements(
                "/FictionBook/description/document-info/date/@value"
            )
        if len(res) == 0:
            is_attrib = 0
            res = self._find_elements_with_namespaces(
                "/fb:FictionBook/fb:description/fb:document-info/fb:date"
            )
        if len(res) == 0:
            is_attrib = 0
            res = self._find_elements("/FictionBook/description/document-info/date")
        if len(res) > 0:
            return res[0] if is_attrib else res[0].text

        return None


class FB2sax(EbookMetaParser):
    """SAX парсер для книг FB2"""

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
            # self.bookfile.__add_author__(" ".join([first_name, last_name]), last_name)
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


class EPub(EbookMetaParser):
    @dataclass
    class Issue(object):
        FIRST_ITEM_NOT_MIMETYPE = 1
        MIMETYPE_ITEM_IS_DEFLATED = 2

    @dataclass
    class Namespace(object):
        XHTML = "http://www.w3.org/1999/xhtml"
        CONTAINER = "urn:oasis:names:tc:opendocument:xmlns:container"
        OPF = "http://www.idpf.org/2007/opf"
        DUBLIN_CORE = "http://purl.org/dc/elements/1.1/"
        ENCRYPTION = "http://www.w3.org/2001/04/xmlenc#"
        DIGITAL_SIGNATURE = "http://www.w3.org/2000/09/xmldsig#"
        MARLIN = "http://marlin-drm.com/epub"
        CALIBRE = "http://calibre.kovidgoyal.net/2009/metadata"

    @dataclass
    class Entry(object):
        MIMETYPE = "mimetype"
        MANIFEST = "META-INF/manifest.xml"
        METADATA = "META-INF/metadata.xml"
        CONTAINER = "META-INF/container.xml"
        ENCRYPTION = "META-INF/encryption.xml"
        RIGHTS = "META-INF/rights.xml"
        SIGNATURES = "META-INF/signatures.xml"

    TOKEN_URL = "https://books.fbreader.org/drm/marlin/get-token"
    CONTENT_ID_PREFIX = "urn:marlin:organization:fbreader.org:0001:"

    ALGORITHM_EMBEDDING = "http://www.idpf.org/2008/embedding"
    ALGORITHM_AES128 = Namespace.ENCRYPTION + "aes128-cbc"

    # class StructureException(Exception):
    #     def __init__(self, message):
    #         Exception.__init__(self, "ePub verification failed: " + message)

    @staticmethod
    def get_parser(file: BytesIO, original_filename) -> EbookMetaParser:
        """Генератор объекта парсера"""

        def get_zip_infolist() -> list[zipfile.ZipInfo]:
            """Вспомогательный метод для извлечения списка содержимого архива"""
            with zipfile.ZipFile(file) as zf:
                return zf.infolist()

        def get_file_from_zip(filename: str | zipfile.ZipInfo) -> bytes:
            """Вспомогательный метод для извлечения файла из архива"""
            with zipfile.ZipFile(file) as zf:
                content = zf.read(filename)
            return content

        file.seek(0, 0)
        zip_file = zipfile.ZipFile(file)

        if zip_file.testzip():
            raise EpubStructureException("broken zip archive")

        infos = get_zip_infolist()
        if len(infos) == 0:
            raise EpubStructureException("empty zip archive")

        mimetype_file = get_file_from_zip(EPub.Entry.MIMETYPE)

        # with zip_file.open(EPub.Entry.MIMETYPE) as mimetype_file:
        # TODO: Зачем делать проверку mimetype_file ?
        if mimetype_file[:30].decode().rstrip("\n\r") != Mimetype.EPUB:
            raise EpubStructureException("'mimetype' item content is incorrect")
        try:
            container_info = get_file_from_zip(EPub.Entry.CONTAINER)
            # TODO: Определить точные исключения и их обработку
        except Exception:
            container_info = None

        root_file = None
        namespaces = {"cont": EPub.Namespace.CONTAINER}

        if container_info:
            tree = etree.fromstring((container_info))
            res = tree.xpath(
                "/cont:container/cont:rootfiles/cont:rootfile", namespaces=namespaces
            )
            if (
                len(res) == 1
                and res[0].get("media-type") == "application/oebps-package+xml"
            ):
                root_file = res[0].get("full-path")
        else:
            opf_infos = [i for i in get_zip_infolist() if i.filename.endswith(".opf")]
            if len(opf_infos) > 1:
                raise EpubStructureException("several OPF files in the archive")
            elif len(opf_infos) == 1:
                root_file = opf_infos[0]
        if root_file:
            root_info = get_file_from_zip(root_file)
        return EPub(file, original_filename, root_info)

    def __init__(self, file, original_filename, root_info):
        super().__init__(file)
        # TODO: Зачем нужно поле issues?
        self.issues = []
        # проверка что переданный файл это непустой zip файл
        file.seek(0, 0)

        infos = self._get_zip_infolist()

        # TODO: Зачем нужно mimetype_info ?
        mimetype_info = infos[0]
        if mimetype_info.filename != EPub.Entry.MIMETYPE:
            self.issues.append(EPub.Issue.FIRST_ITEM_NOT_MIMETYPE)
        elif mimetype_info.compress_type != zipfile.ZIP_STORED:
            self.issues.append(EPub.Issue.MIMETYPE_ITEM_IS_DEFLATED)

        self.book_tree = etree.fromstring(root_info)
        self.book_namespaces = {
            "opf": EPub.Namespace.OPF,
            "dc": EPub.Namespace.DUBLIN_CORE,
        }

    def _get_file_from_zip(self, filename: str | zipfile.ZipInfo) -> bytes:
        """Вспомогательный метод для извлечения файла из архива"""
        with zipfile.ZipFile(self._file) as zf:
            content = zf.read(filename)
        return content

    def _get_zip_infolist(self) -> list[zipfile.ZipInfo]:
        """Вспомогательный метод для извлечения списка содержимого архива"""
        with zipfile.ZipFile(self._file) as zf:
            return zf.infolist()

    def _xpath(self, query: str):
        res = self.book_tree.xpath(query, namespaces=self.book_namespaces)
        return res

    def _get_zip_info(self, path) -> zipfile.ZipInfo:
        with zipfile.ZipFile(self._file) as zf:
            return zf.getinfo(path)

    @property
    def title(self) -> str:
        res = self._xpath("/opf:package/opf:metadata/dc:title")
        if len(res) > 0:
            return res[0].text
        return ""

    @property
    def description(self) -> str:
        res = self._xpath("/opf:package/opf:metadata/dc:description")
        if len(res) > 0 and res[0].text:
            return res[0].text.strip()
        return ""

    @property
    def authors(self) -> list[tuple[str, str]]:
        res = self._xpath('/opf:package/opf:metadata/dc:creator[@role="aut"]')
        if len(res) == 0:
            res = self._xpath("/opf:package/opf:metadata/dc:creator")
        # for node in res:
        #     self.__add_author__(node.text)
        return [n.text for n in res]

    @property
    def tags(self) -> list[str]:
        res = self._xpath("/opf:package/opf:metadata/dc:subject")
        # for node in res:
        #     self.__add_tag__(node.text)
        return [n.text for n in res]

    @property
    def series_info(self):
        res = self._xpath(
            '/opf:package/opf:metadata/opf:meta[@name="calibre:series"]',
        )
        if len(res) > 0:
            series = BookFile.__normalise_string__(res[0].get("content"))
            if series:
                res = self._xpath(
                    '/opf:package/opf:metadata/opf:meta[@name="calibre:series_index"]',
                )
                index = (
                    BookFile.__normalise_string__(res[0].get("content"))
                    if len(res) > 0
                    else None
                )
                return {"title": series, "index": index or None}
        return {}

    @property
    def language_code(self) -> str:
        res = self._xpath("/opf:package/opf:metadata/dc:language")
        if len(res) > 0 and res[0].text:
            return res[0].text.strip()
        return ""

    @property
    def docdate(self) -> str:
        res = self._xpath('/opf:package/opf:metadata/dc:date[@event="modification"]')
        if len(res) == 0:
            res = self._xpath("/opf:package/opf:metadata/dc:date")
        if len(res) > 0:
            return res[0].text
        return ""

        # def __extract_metainfo(self):
        #     root_info = self.__get_root_info()
        #     self.root_filename = root_info.filename
        #     tree = self.__etree_from_entry(root_info)
        # namespaces = {"opf": EPub.Namespace.OPF, "dc": EPub.Namespace.DUBLIN_CORE}

        # res = tree.xpath("/opf:package/opf:metadata/dc:title", namespaces=namespaces)
        # if len(res) > 0:
        #     self.__set_title__(res[0].text)

        # res = tree.xpath(
        #     '/opf:package/opf:metadata/dc:date[@event="modification"]',
        #     namespaces=namespaces,
        # )
        # if len(res) == 0:
        #     res = tree.xpath("/opf:package/opf:metadata/dc:date", namespaces=namespaces)
        # if len(res) > 0:
        #     self.__set_docdate__(res[0].text)

        # res = tree.xpath(
        #     '/opf:package/opf:metadata/dc:creator[@role="aut"]', namespaces=namespaces
        # )
        # if len(res) == 0:
        #     res = tree.xpath(
        #         "/opf:package/opf:metadata/dc:creator", namespaces=namespaces
        #     )
        # for node in res:
        #     self.__add_author__(node.text)

        # res = tree.xpath("/opf:package/opf:metadata/dc:language", namespaces=namespaces)
        # if len(res) > 0 and res[0].text:
        #     self.language_code = res[0].text.strip()

        # res = tree.xpath("/opf:package/opf:metadata/dc:subject", namespaces=namespaces)
        # for node in res:
        #     self.__add_tag__(node.text)

        # res = tree.xpath(
        #     '/opf:package/opf:metadata/opf:meta[@name="calibre:series"]',
        #     namespaces=namespaces,
        # )
        # if len(res) > 0:
        #     series = BookFile.__normalise_string__(res[0].get("content"))
        #     if series:
        #         res = tree.xpath(
        #             '/opf:package/opf:metadata/opf:meta[@name="calibre:series_index"]',
        #             namespaces=namespaces,
        #         )
        #         index = (
        #             BookFile.__normalise_string__(res[0].get("content"))
        #             if len(res) > 0
        #             else None
        #         )
        #         self.series_info = {"title": series, "index": index or None}

        # res = tree.xpath(
        #     "/opf:package/opf:metadata/dc:description", namespaces=namespaces
        # )
        # if len(res) > 0 and res[0].text:
        #     self.description = res[0].text.strip()

        # prefix = os.path.dirname(root_info.filename)
        # if prefix:
        #     prefix += "/"
        # self.cover_fileinfos = self.__find_cover(tree, prefix)

    def __find_cover(self, tree, prefix):
        namespaces = {"opf": EPub.Namespace.OPF, "dc": EPub.Namespace.DUBLIN_CORE}

        def xpath(query):
            return tree.xpath(query, namespaces=namespaces)[0]

        def item_for_href(ref):
            return xpath('/opf:package/opf:manifest/opf:item[@href="%s"]' % ref)

        def image_infos(node):
            path = os.path.normpath(prefix + node.get("href")).replace("\\", "/")
            try:
                fileinfo = self._get_zip_info(path)
            except:
                fileinfo = self._get_zip_info(unquote(path))
            mime = node.get("media-type")
            info = {"filename": fileinfo.filename, "mime": mime}
            if mime.startswith("image/"):
                return [info]
            elif mime == "application/xhtml+xml":
                xhtml = etree.fromstraing(fileinfo)
                xhtml_prefix = os.path.dirname(fileinfo.filename) + "/"
                img = xhtml.xpath(
                    "//xhtml:img[@src]", namespaces={"xhtml": EPub.Namespace.XHTML}
                )[0]
                return [
                    info,
                    {
                        "filename": os.path.normpath(xhtml_prefix + img.get("src")),
                        # TODO: detect mimetype
                        "mime": "image/auto",
                    },
                ]
            else:
                raise Exception("unknown mimetype %s" % mime)

        try:
            node = xpath(
                '/opf:package/opf:manifest/opf:item[@properties="cover-image"]'
            )
            return image_infos(node)
        except Exception:
            pass

        try:
            node = xpath('/opf:package/opf:metadata/opf:meta[@name="cover"]')
            return image_infos(
                xpath(
                    '/opf:package/opf:manifest/opf:item[@id="%s"]' % node.get("content")
                )
            )
        except Exception:
            pass

        try:
            node = xpath('/opf:package/opf:metadata/meta[@name="cover"]')
            return image_infos(
                xpath(
                    '/opf:package/opf:manifest/opf:item[@id="%s"]' % node.get("content")
                )
            )
        except Exception:
            pass

        try:
            node = xpath('/package/metadata/meta[@name="cover"]')
            return image_infos(
                xpath('/package/manifest/item[@id="%s"]' % node.get("content"))
            )
        except Exception:
            pass

        try:
            node = xpath(
                '/opf:package/opf:guide/opf:reference[@type="other.ms-coverimage-standard"][@title="Cover"]'
            )
            return image_infos(item_for_href(node.get("href")))
        except Exception:
            pass

        try:
            node = xpath(
                '/opf:package/opf:guide/opf:reference[@type="other.ms-coverimage-standard"]'
            )
            return image_infos(item_for_href(node.get("href")))
        except Exception:
            pass

        try:
            node = xpath('/opf:package/opf:manifest/opf:item[@id="cover"]')
            return image_infos(node)
        except Exception:
            pass

        return []

    def __get_root_info(self) -> zipfile.ZipInfo:
        try:
            container_info: zipfile.ZipInfo | None = self._get_zip_info(
                EPub.Entry.CONTAINER
            )
        except KeyError:
            container_info = None
        if container_info:
            tree = etree.fromstring(self._get_file_from_zip(container_info))
            root_file = None
            namespaces = {"cont": EPub.Namespace.CONTAINER}
            res = tree.xpath(
                "/cont:container/cont:rootfiles/cont:rootfile", namespaces=namespaces
            )
            if (
                len(res) == 1
                and res[0].get("media-type") == "application/oebps-package+xml"
            ):
                root_file = res[0].get("full-path")
            if root_file:
                return self._get_zip_info(root_file)
        else:
            opf_infos: list[zipfile.ZipInfo] = [
                i for i in self._get_zip_infolist() if i.filename.endswith(".opf")
            ]
            if len(opf_infos) > 1:
                raise EpubStructureException("several OPF files in the archive")
            elif len(opf_infos) == 1:
                return opf_infos[0]

        raise EpubStructureException("OPF entry not found")

    def __contains_entry(self, name) -> bool:
        try:
            self._get_zip_info(name)
            return True
        except KeyError:
            return False

    def __extract_content_ids(self):
        content_ids = set()
        try:
            tree = etree.fromstring(self._get_file_from_zip(EPub.Entry.ENCRYPTION))
            ns = {
                "c": EPub.Namespace.CONTAINER,
                "e": EPub.Namespace.ENCRYPTION,
                "d": EPub.Namespace.DIGITAL_SIGNATURE,
            }
            res = tree.xpath(
                "/c:encryption/e:EncryptedData/d:KeyInfo/d:KeyName", namespaces=ns
            )
            for node in res:
                key_name = res[0].text
                if key_name and key_name.startswith(EPub.CONTENT_ID_PREFIX):
                    content_ids.add(key_name[len(EPub.CONTENT_ID_PREFIX) :])
        except:
            pass
        return list(content_ids)

    def get_encryption_info(self):
        UNKNOWN_ENCRYPTION = {"method": "unknown"}

        algo = None

        if self.__contains_entry(EPub.Entry.ENCRYPTION):
            try:
                tree = etree.fromstring(self._get_file_from_zip(EPub.Entry.ENCRYPTION))
                namespaces = {
                    "c": EPub.Namespace.CONTAINER,
                    "e": EPub.Namespace.ENCRYPTION,
                }
                res = tree.xpath(
                    "/c:encryption/e:EncryptedData/e:EncryptionMethod",
                    namespaces=namespaces,
                )
                algorithms = list(set([r.get("Algorithm") for r in res]))
                if len(algorithms) != 1:
                    return {"method": "multi", "ids": algorithms}
                if algorithms[0] == EPub.ALGORITHM_EMBEDDING:
                    return {"method": "embedding"}
                elif algorithms[0] == EPub.ALGORITHM_AES128:
                    algo = algorithms[0]
                else:
                    return UNKNOWN_ENCRYPTION
            except:
                return UNKNOWN_ENCRYPTION

        if self.__contains_entry(EPub.Entry.RIGHTS):
            if algo == EPub.ALGORITHM_AES128:
                try:
                    tree = etree.fromstring(self._get_file_from_zip(EPub.Entry.RIGHTS))
                    namespaces = {"m": EPub.Namespace.MARLIN}
                    res = tree.xpath(
                        "/m:Marlin/m:RightsURL/m:RightsIssuer/m:URL",
                        namespaces=namespaces,
                    )
                    if res:
                        token_url = res[0].text
                        content_ids = (
                            self.__extract_content_ids()
                            if token_url == EPub.TOKEN_URL
                            else []
                        )
                        return {
                            "method": "marlin",
                            "token_url": token_url,
                            "content_ids": content_ids,
                        }
                except:
                    pass
            return UNKNOWN_ENCRYPTION

        if self.__contains_entry(EPub.Entry.SIGNATURES):
            return UNKNOWN_ENCRYPTION

        return {}

    def __save_tree(self, zip_file, filename, tree, working_dir):
        path = os.path.join(working_dir, filename)
        with open(path, "w") as pfile:
            tree.write(pfile, pretty_print=True)
        zip_file.write(path, arcname=filename)

    def __add_encryption_section(self, index, root, uri, content_id):
        # See http://www.marlin-community.com/files/marlin-EPUB-extension-v1.0.pdf
        # section 4.2.1
        key_name = EPub.CONTENT_ID_PREFIX + content_id

        enc_data = etree.SubElement(
            root,
            etree.QName(EPub.Namespace.ENCRYPTION, "EncryptedData"),
            Id="ED%d" % index,
        )
        etree.SubElement(
            enc_data,
            etree.QName(EPub.Namespace.ENCRYPTION, "EncryptionMethod"),
            Algorithm=EPub.Namespace.ENCRYPTION + "aes128-cbc",
        )
        key_info = etree.SubElement(
            enc_data, etree.QName(EPub.Namespace.DIGITAL_SIGNATURE, "KeyInfo")
        )
        key_name_tag = etree.SubElement(
            key_info, etree.QName(EPub.Namespace.DIGITAL_SIGNATURE, "KeyName")
        )
        key_name_tag.text = key_name
        cipher_data = etree.SubElement(
            enc_data, etree.QName(EPub.Namespace.ENCRYPTION, "CipherData")
        )
        etree.SubElement(
            cipher_data,
            etree.QName(EPub.Namespace.ENCRYPTION, "CipherReference"),
            URI=uri,
        )

    # def __create_encryption_file(
    #     self, zip_file, working_dir, encrypted_files, content_id
    # ):
    #     namespaces = {
    #         None: EPub.Namespace.CONTAINER,
    #         "enc": EPub.Namespace.ENCRYPTION,
    #         "ds": EPub.Namespace.DIGITAL_SIGNATURE,
    #     }
    #     root = etree.Element(
    #         etree.QName(EPub.Namespace.CONTAINER, "encryption"), nsmap=namespaces
    #     )
    #     tree = etree.ElementTree(root)
    #
    #     index = 1
    #     for filename in encrypted_files:
    #         self.__add_encryption_section(index, root, filename, content_id)
    #         index += 1
    #
    #     self.__save_tree(zip_file, EPub.Entry.ENCRYPTION, tree, working_dir)
    #
    # def __create_rights_file(self, zip_file, working_dir):
    #     namespaces = {None: EPub.Namespace.MARLIN}
    #     root = etree.Element(
    #         etree.QName(EPub.Namespace.MARLIN, "Marlin"), nsmap=namespaces
    #     )
    #     tree = etree.ElementTree(root)
    #     etree.SubElement(
    #         root, etree.QName(EPub.Namespace.MARLIN, "Version")
    #     ).text = "1.0"
    #     rights_url = etree.SubElement(
    #         root, etree.QName(EPub.Namespace.MARLIN, "RightsURL")
    #     )
    #     rights_issuer = etree.SubElement(
    #         rights_url, etree.QName(EPub.Namespace.MARLIN, "RightsIssuer")
    #     )
    #     etree.SubElement(
    #         rights_issuer, etree.QName(EPub.Namespace.MARLIN, "URL")
    #     ).text = EPub.TOKEN_URL
    #     self.__save_tree(zip_file, EPub.Entry.RIGHTS, tree, working_dir)

    # def encrypt(self, key, content_id, working_dir, files_to_keep=None):
    #     if self.get_encryption_info():
    #         raise Exception(
    #             "Cannot encrypt file %s, it is already encrypted" % self._file.name
    #         )
    #
    #     if not files_to_keep:
    #         files_to_keep = [
    #             EPub.Entry.MANIFEST,
    #             EPub.Entry.METADATA,
    #             EPub.Entry.CONTAINER,
    #         ]
    #         files_to_keep += [self.root_filename]
    #         files_to_keep += [info["filename"] for info in self.cover_fileinfos]
    #
    #     self._zip_file.extractall(path=working_dir)
    #
    #     new_epub = mkstemp(dir=working_dir)
    #     with zipfile.ZipFile(new_epub, "w", zipfile.ZIP_DEFLATED) as zip_file:
    #         zip_file.writestr(EPub.Entry.MIMETYPE, Mimetype.EPUB, zipfile.ZIP_STORED)
    #         encrypted_files = []
    #         for entry in [
    #             info.filename
    #             for info in list_zip_file_infos(self.__zip_file)
    #             if info.filename != EPub.Entry.MIMETYPE
    #         ]:
    #             path = os.path.join(working_dir, entry)
    #             if entry in files_to_keep:
    #                 zip_file.write(path, arcname=entry)
    #             else:
    #                 encrypt(os.path.join(working_dir, entry), key, working_dir)
    #                 encrypted_files.append(entry)
    #                 zip_file.write(
    #                     path, arcname=entry, compress_type=zipfile.ZIP_STORED
    #                 )
    #         self.__create_encryption_file(
    #             zip_file, working_dir, encrypted_files, content_id
    #         )
    #         self.__create_rights_file(zip_file, working_dir)
    #     shutil.move(new_epub, self.path)
    #     self.close()
    #     self.__initialize()
    #
    # def repair(self, working_dir):
    #     self._zip_file.extractall(path=working_dir)
    #
    #     new_epub = mkstemp(dir=working_dir)
    #     with zipfile.ZipFile(new_epub, "w", zipfile.ZIP_DEFLATED) as zip_file:
    #         zip_file.writestr(EPub.Entry.MIMETYPE, Mimetype.EPUB, zipfile.ZIP_STORED)
    #         for entry in [
    #             info.filename
    #             for info in list_zip_file_infos(self.__zip_file)
    #             if info.filename != EPub.Entry.MIMETYPE
    #         ]:
    #             zip_file.write(os.path.join(working_dir, entry), arcname=entry)
    #     shutil.move(new_epub, self.path)
    #     self.close()
    #     self.__initialize()

    # def extract_cover_internal(self, working_dir):
    #     if len(self.cover_fileinfos) == 0:
    #         return (None, False)
    #     name = self.cover_fileinfos[-1]["filename"]
    #     self._zip_file.extract(name, path=working_dir)
    #     split = [part for part in name.split("/") if part]
    #     if len(split) > 1:
    #         shutil.move(
    #             os.path.join(working_dir, name), os.path.join(working_dir, split[-1])
    #         )
    #         shutil.rmtree(os.path.join(working_dir, split[0]))
    #     return (split[-1] if len(split) > 0 else None, False)
    #
    # def extract_cover_memory(self):
    #     if len(self.cover_fileinfos) == 0:
    #         return None
    #     name = self.cover_fileinfos[-1]["filename"]
    #     content = self._zip_file.open(name).read()
    #     return content
