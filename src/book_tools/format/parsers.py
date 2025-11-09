# Парсеры для разных форматов электронных книг

import base64
import zipfile
from abc import ABC, abstractmethod
from io import BytesIO
from lxml import etree
from dataclasses import dataclass
from book_tools.format.util import strip_symbols

import logging

from book_tools.format.util import list_zip_file_infos
from .mimetype import Mimetype
from book_tools.exceptions import FB2StructureException
from book_tools.format.fb2sax import fb2parser


@dataclass
class Namespace(object):
    """Возможные пространства имен в xml файле fb2"""

    FICTION_BOOK20: str = "http://www.gribuser.ru/xml/fictionbook/2.0"
    FICTION_BOOK21: str = "http://www.gribuser.ru/xml/fictionbook/2.1"
    XLINK: str = "http://www.w3.org/1999/xlink"


class EbookMetaParser(ABC):
    """Абстрактный класс парсера для электронной книги"""

    ns_map = {"fb": Namespace.FICTION_BOOK20, "l": Namespace.XLINK}

    def __init__(self, file: BytesIO):
        self._file = file

    @abstractmethod
    def extract_cover(self) -> BytesIO | None: ...

    @property
    @abstractmethod
    def title(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> bytes | None: ...

    @property
    @abstractmethod
    def authors(self) -> list[tuple[str, str]]: ...

    @property
    @abstractmethod
    def tags(self) -> list[str]: ...

    @property
    @abstractmethod
    def series_info(self) -> dict[str, str]: ...

    @property
    @abstractmethod
    def language_code(self) -> str: ...

    @property
    @abstractmethod
    def docdate(self) -> str: ...


class FB2Base(EbookMetaParser):
    """Базовый класс для извлечения метаданных из книг в формате FB2 с помощью lxml"""

    def __init__(self, file: BytesIO, original_filename: str, mimetype: str):
        """
        Инициализация объекта. Автоматически устанавливает параметры
            __namespaces
            _mimetype

        Параметры инициализации
        -----------------------
            file: BytesIO
                Cодержимое файла книги для парсинга

            original_filename: str
                Наименовние оригинального файла книги. Если файл размещен в ФС, то это наименование файла в ФС.
                Если файл книги находится в zip архиве, то это наименование файла внутри архива.

            mimetype: str
                Тип данных MIME для книги. Может быть либо Mimetype.FB2 либо Mimetype.FB2_ZIP
        """
        # Инициализация полей объекта
        self._etree: etree._ElementTree = None
        self._namespaces: dict[str, str] = {}
        self._log = logging.getLogger(str(self.__class__))

        # Парсинг полученного содержимого файла
        try:
            file.seek(0, 0)
            self._etree = etree.parse(file)
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
            self._namespaces["fb"] = Namespace.FICTION_BOOK20
        if "l" not in self._namespaces.keys():
            self._namespaces["l"] = Namespace.XLINK

    def extract_cover(self):
        try:
            res: str = self._etree.xpath(
                "/fb:FictionBook/fb:description/fb:title-info/fb:coverpage/fb:image",
                namespaces=self._namespaces,
            )
            if len(res) == 0:
                res = self._etree.xpath(
                    "/fb:FictionBook/fb:body//fb:image", namespaces=self._namespaces
                )
            cover_id: str = res[0].get("{" + Namespace.XLINK + "}href")[1:]
            # print(cover_id)
            res = self._etree.xpath(
                '/fb:FictionBook/fb:binary[@id="%s"]' % cover_id,
                namespaces=self._namespaces,
            )
            content = base64.b64decode(res[0].text)
            return content
        except Exception as err:
            print("exception Extract %s" % err)
            return None

    @property
    def title(self) -> str:
        res = self._etree.xpath(
            "/fb:FictionBook/fb:description/fb:title-info/fb:book-title",
            namespaces=self._namespaces,
        )
        if len(res) == 0:
            res = self._etree.xpath(
                '/*[local-name() = "FictionBook"]/*[local-name() = "description"]/*[local-name() = "title-info"]/*[local-name() = "book-title"]'
            )
        if len(res) > 0:
            res = res[0].text
            # self.__set_title__(res[0].text)

        return res

    @property
    def description(self) -> bytes | None:
        res = self._etree.xpath(
            "/fb:FictionBook/fb:description/fb:title-info/fb:annotation",
            namespaces=self._namespaces,
        )
        if len(res) == 0:
            res = self._etree.xpath("/FictionBook/description/title-info/annotation")
        if len(res) > 0:
            return etree.tostring(res[0], encoding="utf-8", method="text")

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

        res = self._etree.xpath(
            "/fb:FictionBook/fb:description/fb:title-info/fb:author",
            namespaces=self._namespaces,
        )
        if len(res) == 0:
            use_namespaces = False
            res = self._etree.xpath("/FictionBook/description/title-info/author")

        authors: list[tuple[str, str]] = []
        for node in res:
            authors.append(add_author_from_node(node))
        return authors

    @property
    def tags(self) -> list[str]:
        res = self._etree.xpath(
            "/fb:FictionBook/fb:description/fb:title-info/fb:genre",
            namespaces=self._namespaces,
        )
        if len(res) == 0:
            # use_namespaces = False
            res = self._etree.xpath("/FictionBook/description/title-info/genre")
        tags: list[str] = []
        for node in res:
            # self.__add_tag__(node.text)
            tags.append(node.text)
        return tags

    @property
    def series_info(self):
        res = self._etree.xpath(
            "/fb:FictionBook/fb:description/fb:title-info/fb:sequence",
            namespaces=self._namespaces,
        )
        if len(res) == 0:
            # use_namespaces = False
            res = self._etree.xpath("/FictionBook/description/title-info/sequence")
        if len(res) > 0:
            title = res[0].get("name")
            index = res[0].get("number")

            if title:
                # self.series_info = {"title": title, "index": index}
                return {"title": title, "index": index}
        return None

    @property
    def language_code(self):
        res = self._etree.xpath(
            "/fb:FictionBook/fb:description/fb:title-info/fb:lang",
            namespaces=self._namespaces,
        )
        if len(res) == 0:
            res = self._etree.xpath("/FictionBook/description/title-info/lang")
        if len(res) > 0:
            return res[0].text
        return None

    @property
    def docdate(self):
        # TODO оптимизация выдачи результата
        is_attrib: int = 1
        res = self._etree.xpath(
            "/fb:FictionBook/fb:description/fb:document-info/fb:date/@value",
            namespaces=self._namespaces,
        )
        if len(res) == 0:
            res = self._etree.xpath(
                "/FictionBook/description/document-info/date/@value"
            )
        if len(res) == 0:
            is_attrib = 0
            res = self._etree.xpath(
                "/fb:FictionBook/fb:description/fb:document-info/fb:date",
                namespaces=self._namespaces,
            )
        if len(res) == 0:
            is_attrib = 0
            res = self._etree.xpath("/FictionBook/description/document-info/date")
        if len(res) > 0:
            # self.__set_docdate__(res[0] if is_attrib else res[0].text)
            return res[0] if is_attrib else res[0].text

        return None


class FB2(FB2Base):
    def __init__(self, file, original_filename):
        FB2Base.__init__(self, file, original_filename, Mimetype.FB2)

    def __create_tree__(self, file):
        try:
            file.seek(0, 0)
            return etree.parse(file)
        except Exception as err:
            raise FB2StructureException("the file is not a valid XML (%s)" % err)


class FB2Zip(FB2Base):
    def __init__(self, file: BytesIO, original_filename: str):
        with zipfile.ZipFile(file, "r") as test:
            if test.testzip():
                # некорректный zip файл
                raise FB2StructureException("broken zip archive")
            count = len(list_zip_file_infos(test))
            if count != 1:
                raise FB2StructureException("archive contains %s files" % count)

        FB2Base.__init__(self, file, original_filename, Mimetype.FB2_ZIP)

    def __create_tree__(self, file: BytesIO):
        book = BytesIO()
        with zipfile.ZipFile(file, "r") as zip:
            bookname = list_zip_file_infos(zip)[0]
            with zip.open(bookname, "r") as bf:
                book.write(bf.read())

            # with self.__zip_file.open(self.__infos[0]) as entry:
        book.seek(0, 0)
        try:
            return etree.parse(book)
        except Exception:
            raise FB2StructureException(
                # "'%s' is not a valid XML" % self.__infos[0].filename
                "'%s' is not a valid XML" % bookname
            )

    # def __exit__(self, kind, value, traceback):
    #     self.__zip_file.__exit__(kind, value, traceback)
    #     pass


class FB2sax(EbookMetaParser):
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
