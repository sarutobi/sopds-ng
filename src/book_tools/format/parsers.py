# Парсеры для разных форматов электронных книг

import base64
import zipfile
from abc import ABC, abstractmethod
from io import BytesIO
from lxml import etree

from book_tools.format.util import list_zip_file_infos
from .bookfile import BookFile
from .fb2 import Namespace
from .mimetype import Mimetype
from book_tools.exceptions import FB2StructureException


class EbookMetaParser(ABC):
    """Абстрактный класс парсера для электронной книги"""

    def __init__(self, file: BytesIO):
        self._file = file

    @abstractmethod
    def parse_book(self) -> None: ...

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

        self.__namespaces: dict[str, str] = {
            "fb": Namespace.FICTION_BOOK20,
            "xlink": Namespace.XLINK,
        }
        self._mimetype: str = ""
        self._etree: etree._ElementTree = None

    # @abstractmethod
    # def __create_tree__(self, file: BytesIO) -> etree._ElementTree: ...

    def parse_book(self, file) -> None:
        try:
            file.seek(0, 0)
            self._etree = etree.parse(file)
            if self._etree.getroot().tag.find(Namespace.FICTION_BOOK21) > 0:
                self.__namespaces["fb"] = Namespace.FICTION_BOOK21
        except Exception as err:
            raise FB2StructureException("the file is not a valid XML (%s)" % err)

    def extract_cover(self):
        try:
            res: str = self._etree.xpath(
                "/fb:FictionBook/fb:description/fb:title-info/fb:coverpage/fb:image",
                namespaces=self.__namespaces,
            )
            if len(res) == 0:
                res = self._etree.xpath(
                    "/fb:FictionBook/fb:body//fb:image", namespaces=self.__namespaces
                )
            cover_id: str = res[0].get("{" + Namespace.XLINK + "}href")[1:]
            # print(cover_id)
            res = self._etree.xpath(
                '/fb:FictionBook/fb:binary[@id="%s"]' % cover_id,
                namespaces=self.__namespaces,
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
            namespaces=self.__namespaces,
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
            namespaces=self.__namespaces,
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
                subnode = node.find("fb:" + name, namespaces=self.__namespaces)
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
            namespaces=self.__namespaces,
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
            namespaces=self.__namespaces,
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
            namespaces=self.__namespaces,
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
            namespaces=self.__namespaces,
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
            namespaces=self.__namespaces,
        )
        if len(res) == 0:
            res = self._etree.xpath(
                "/FictionBook/description/document-info/date/@value"
            )
        if len(res) == 0:
            is_attrib = 0
            res = self._etree.xpath(
                "/fb:FictionBook/fb:description/fb:document-info/fb:date",
                namespaces=self.__namespaces,
            )
        if len(res) == 0:
            is_attrib = 0
            res = self._etree.xpath("/FictionBook/description/document-info/date")
        if len(res) > 0:
            # self.__set_docdate__(res[0] if is_attrib else res[0].text)
            return res[0] if is_attrib else res[0].text

        return None

    # def parse_book_data(self, file, original_filename, mimetype) -> BookFile:
    #     bookfile = BookFile(file, original_filename, mimetype)
    #     tree = self.__create_tree__(file)
    #     self.__detect_namespaces(tree)
    #     bookfile.__set_title__(self.__detect_title(tree))
    #     for author, sortkey in self.__detect_authors(tree):
    #         bookfile.__add_author__(author, sortkey)
    #     for tag in self.__detect_tags(tree):
    #         bookfile.__add_tag__(tag)
    #     bookfile.series_info = self.__detect_series_info(tree)
    #     bookfile.language_code = self.__detect_language(tree)
    #     bookfile.__set_docdate__(self.__detect_docdate(tree))
    #     bookfile.description = self.__detect_description(tree)
    #     return bookfile

    # def extract_cover_internal(self, file, working_dir):
    #     # TODO сохранение обложки в отдельный файл это не функция парсера
    #     try:
    #         tree = self.__create_tree__(file)
    #         res = tree.xpath(
    #             "/fb:FictionBook/fb:description/fb:title-info/fb:coverpage/fb:image",
    #             namespaces=self.__namespaces,
    #         )
    #         cover_id = res[0].get("{" + Namespace.XLINK + "}href")[1:]
    #         res = tree.xpath(
    #             '/fb:FictionBook/fb:binary[@id="%s"]' % cover_id,
    #             namespaces=self.__namespaces,
    #         )
    #         content = base64.b64decode(res[0].text)
    #         with open(os.path.join(working_dir, "cover.jpeg"), "wb") as cover_file:
    #             cover_file.write(content)
    #         return ("cover.jpeg", False)
    #     except Exception:
    #         return (None, False)

    # def extract_cover_memory(self, file):
    #     try:
    #         tree = self.__create_tree__(file)
    #         res = tree.xpath(
    #             "/fb:FictionBook/fb:description/fb:title-info/fb:coverpage/fb:image",
    #             namespaces=self.__namespaces,
    #         )
    #         if len(res) == 0:
    #             res = tree.xpath(
    #                 "/fb:FictionBook/fb:body//fb:image", namespaces=self.__namespaces
    #             )
    #         cover_id = res[0].get("{" + Namespace.XLINK + "}href")[1:]
    #         # print(cover_id)
    #         res = tree.xpath(
    #             '/fb:FictionBook/fb:binary[@id="%s"]' % cover_id,
    #             namespaces=self.__namespaces,
    #         )
    #         content = base64.b64decode(res[0].text)
    #         return content
    #     except Exception as err:
    #         print("exception Extract %s" % err)
    #         return None
    #
    # def __detect_namespaces(self, tree):
    #     if tree.getroot().tag.find(Namespace.FICTION_BOOK21) > 0:
    #         self.__namespaces["fb"] = Namespace.FICTION_BOOK21
    #     return None
    #
    # def __detect_title(self, tree):
    #     res = tree.xpath(
    #         "/fb:FictionBook/fb:description/fb:title-info/fb:book-title",
    #         namespaces=self.__namespaces,
    #     )
    #     if len(res) == 0:
    #         res = tree.xpath(
    #             '/*[local-name() = "FictionBook"]/*[local-name() = "description"]/*[local-name() = "title-info"]/*[local-name() = "book-title"]'
    #         )
    #     if len(res) > 0:
    #         res = res[0].text
    #         # self.__set_title__(res[0].text)
    #
    #     return res
    #
    # def __detect_docdate(self, tree):
    #     is_attrib = 1
    #     res = tree.xpath(
    #         "/fb:FictionBook/fb:description/fb:document-info/fb:date/@value",
    #         namespaces=self.__namespaces,
    #     )
    #     if len(res) == 0:
    #         res = tree.xpath("/FictionBook/description/document-info/date/@value")
    #     if len(res) == 0:
    #         is_attrib = 0
    #         res = tree.xpath(
    #             "/fb:FictionBook/fb:description/fb:document-info/fb:date",
    #             namespaces=self.__namespaces,
    #         )
    #     if len(res) == 0:
    #         is_attrib = 0
    #         res = tree.xpath("/FictionBook/description/document-info/date")
    #     if len(res) > 0:
    #         # self.__set_docdate__(res[0] if is_attrib else res[0].text)
    #         return res[0] if is_attrib else res[0].text
    #
    #     return None
    #
    # def __detect_authors(self, tree):
    #     use_namespaces = True
    #
    #     def subnode_text(node, name):
    #         if use_namespaces:
    #             subnode = node.find("fb:" + name, namespaces=self.__namespaces)
    #         else:
    #             subnode = node.find(name)
    #         text = subnode.text if subnode is not None else ""
    #         return text or ""
    #
    #     def add_author_from_node(node):
    #         first_name = subnode_text(node, "first-name")
    #         # middle_name = subnode_text(node, 'middle-name')
    #         last_name = subnode_text(node, "last-name")
    #         # self.__add_author__(" ".join([first_name, last_name]), last_name)
    #         return (" ".join([first_name, last_name]), last_name)
    #
    #     res = tree.xpath(
    #         "/fb:FictionBook/fb:description/fb:title-info/fb:author",
    #         namespaces=self.__namespaces,
    #     )
    #     if len(res) == 0:
    #         use_namespaces = False
    #         res = tree.xpath("/FictionBook/description/title-info/author")
    #
    #     for node in res:
    #         yield add_author_from_node(node)
    #
    # def __detect_language(self, tree):
    #     res = tree.xpath(
    #         "/fb:FictionBook/fb:description/fb:title-info/fb:lang",
    #         namespaces=self.__namespaces,
    #     )
    #     if len(res) == 0:
    #         # use_namespaces = False
    #         res = tree.xpath("/FictionBook/description/title-info/lang")
    #     if len(res) > 0:
    #         # self.language_code = res[0].text
    #         return res[0].text
    #     return None
    #
    # def __detect_tags(self, tree):
    #     res = tree.xpath(
    #         "/fb:FictionBook/fb:description/fb:title-info/fb:genre",
    #         namespaces=self.__namespaces,
    #     )
    #     if len(res) == 0:
    #         # use_namespaces = False
    #         res = tree.xpath("/FictionBook/description/title-info/genre")
    #     for node in res:
    #         # self.__add_tag__(node.text)
    #         yield node.text

    # def __detect_series_info(self, tree):
    #     res = tree.xpath(
    #         "/fb:FictionBook/fb:description/fb:title-info/fb:sequence",
    #         namespaces=self.__namespaces,
    #     )
    #     if len(res) == 0:
    #         # use_namespaces = False
    #         res = tree.xpath("/FictionBook/description/title-info/sequence")
    #     if len(res) > 0:
    #         title = BookFile.__normalise_string__(res[0].get("name"))
    #         index = BookFile.__normalise_string__(res[0].get("number"))
    #
    #         if title:
    #             # self.series_info = {"title": title, "index": index}
    #             return {"title": title, "index": index}
    #     return None

    # def __detect_description(self, tree):
    #     res = tree.xpath(
    #         "/fb:FictionBook/fb:description/fb:title-info/fb:annotation",
    #         namespaces=self.__namespaces,
    #     )
    #     if len(res) == 0:
    #         res = tree.xpath("/FictionBook/description/title-info/annotation")
    #     if len(res) > 0:
    #         return etree.tostring(res[0], encoding="utf-8", method="text")
    #
    #     return None


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
