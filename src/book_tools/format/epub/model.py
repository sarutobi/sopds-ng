"""
Основной класс EPUB.
"""

import os
import shutil
import urllib.parse
import zipfile
from tempfile import mkstemp

from lxml import etree

from book_tools.exceptions import ParserError
from book_tools.format.bookfile import BookFile
from book_tools.format.epub.constants import Entry, Issue, Namespace
from book_tools.format.epub.cover import EPubCoverFinder
from book_tools.format.epub.encryption import EPubEncryptionHandler
from book_tools.format.epub.metadata import EPubMetadataParser
from book_tools.format.mimetype import Mimetype
from book_tools.format.util import list_zip_file_infos, normalize_string


class EPub(BookFile):
    TOKEN_URL = "https://books.fbreader.org/drm/marlin/get-token"
    CONTENT_ID_PREFIX = "urn:marlin:organization:fbreader.org:0001:"

    ALGORITHM_EMBEDDING = "http://www.idpf.org/2008/embedding"
    ALGORITHM_AES128 = Namespace.ENCRYPTION + "aes128-cbc"

    class StructureException(ParserError):
        def __init__(self, message):
            Exception.__init__(self, "ePub verification failed: " + message)

    def __init__(self, file, original_filename):
        BookFile.__init__(self, file, original_filename, Mimetype.EPUB)
        self.root_filename = None
        self.cover_fileinfos = []

        self._zip_file = None
        self.__initialize()

    def __initialize(self):
        self.file.seek(0, 0)
        self._zip_file = zipfile.ZipFile(self.file)
        self.issues = []
        try:
            if self._zip_file.testzip():
                raise EPub.StructureException("broken zip archive")

            infos = self._zip_file.infolist()
            if len(infos) == 0:
                raise EPub.StructureException("empty zip archive")

            mimetype_info = infos[0]
            if mimetype_info.filename != Entry.MIMETYPE:
                self.issues.append(Issue.FIRST_ITEM_NOT_MIMETYPE)
            elif mimetype_info.compress_type != zipfile.ZIP_STORED:
                self.issues.append(Issue.MIMETYPE_ITEM_IS_DEFLATED)

            with self._zip_file.open(Entry.MIMETYPE) as mimetype_file:
                if mimetype_file.read(30).decode().rstrip("\n\r") != Mimetype.EPUB:
                    raise EPub.StructureException(
                        "'mimetype' item content is incorrect"
                    )

            self.__extract_metainfo()
        except EPub.StructureException as error:
            self.close()
            raise error
        except Exception as error:
            self.close()
            raise EPub.StructureException(str(error))

    def close(self):
        if self._zip_file:
            self._zip_file.close()

    def __exit__(self, kind, value, traceback):
        self.close()

    def _etree_from_entry(self, info):
        with self._zip_file.open(info) as entry:
            data = entry.read(1048576)
            try:
                return etree.fromstring(data)
            except Exception:
                for encoding in ("utf-8", "cp1251"):
                    try:
                        return etree.fromstring(data.decode(encoding))
                    except Exception:
                        continue
                raise EPub.StructureException(
                    "'" + info.filename + "' is not a valid XML"
                )

    def __extract_metainfo(self):
        root_info = self.__get_root_info()
        self.root_filename = root_info.filename
        tree = self._etree_from_entry(root_info)

        parser = EPubMetadataParser(self)
        metadata = parser.parse(tree, root_info)

        # Apply metadata to self
        if metadata.get("title"):
            self.__set_title__(metadata["title"])
        if metadata.get("docdate"):
            self.__set_docdate__(metadata["docdate"])
        for author in metadata.get("authors", []):
            self.__add_author__(author)
        if metadata.get("language_code"):
            self.language_code = metadata["language_code"]
        for tag in metadata.get("tags", []):
            self.__add_tag__(tag)
        if metadata.get("series_info"):
            self.series_info = metadata["series_info"]
        if metadata.get("description"):
            self.description = metadata["description"]

        prefix = os.path.dirname(root_info.filename)
        if prefix:
            prefix += "/"

        cover_finder = EPubCoverFinder(self)
        self.cover_fileinfos = cover_finder.find_cover(tree, prefix)

    def __get_root_info(self):
        try:
            container_info = self._zip_file.getinfo(Entry.CONTAINER)
        except Exception:
            container_info = None
        if container_info:
            tree = self._etree_from_entry(container_info)
            root_file = None
            namespaces = {"cont": Namespace.CONTAINER}
            res = tree.xpath(
                "/cont:container/cont:rootfiles/cont:rootfile", namespaces=namespaces
            )
            if (
                len(res) == 1
                and res[0].get("media-type") == "application/oebps-package+xml"
            ):
                root_file = res[0].get("full-path")
            if root_file:
                return self._zip_file.getinfo(root_file)
        else:
            opf_infos = [
                i for i in self._zip_file.infolist() if i.filename.endswith(".opf")
            ]
            if len(opf_infos) > 1:
                raise EPub.StructureException("several OPF files in the archive")
            elif len(opf_infos) == 1:
                return opf_infos[0]

        raise EPub.StructureException("OPF entry not found")

    def get_encryption_info(self):
        handler = EPubEncryptionHandler(self)
        return handler.get_encryption_info()

    def __save_tree(self, zip_file, filename, tree, working_dir):
        path = os.path.join(working_dir, filename)
        with open(path, "w") as pfile:
            tree.write(pfile, pretty_print=True)
        zip_file.write(path, arcname=filename)

    def __create_rights_file(self, zip_file, working_dir):
        namespaces = {None: Namespace.MARLIN}
        root = etree.Element(etree.QName(Namespace.MARLIN, "Marlin"), nsmap=namespaces)
        tree = etree.ElementTree(root)
        etree.SubElement(root, etree.QName(Namespace.MARLIN, "Version")).text = "1.0"
        rights_url = etree.SubElement(root, etree.QName(Namespace.MARLIN, "RightsURL"))
        rights_issuer = etree.SubElement(
            rights_url, etree.QName(Namespace.MARLIN, "RightsIssuer")
        )
        etree.SubElement(
            rights_issuer, etree.QName(Namespace.MARLIN, "URL")
        ).text = self.TOKEN_URL
        self.__save_tree(zip_file, Entry.RIGHTS, tree, working_dir)

    def extract_cover_internal(self, working_dir):
        if len(self.cover_fileinfos) == 0:
            return (None, False)
        name = self.cover_fileinfos[-1]["filename"]
        self._zip_file.extract(name, path=working_dir)
        split = [part for part in name.split("/") if part]
        if len(split) > 1:
            shutil.move(
                os.path.join(working_dir, name), os.path.join(working_dir, split[-1])
            )
            shutil.rmtree(os.path.join(working_dir, split[0]))
        return (split[-1] if len(split) > 0 else None, False)

    def extract_cover_memory(self):
        if len(self.cover_fileinfos) == 0:
            return None
        name = self.cover_fileinfos[-1]["filename"]
        content = self._zip_file.open(name).read()
        return content

    def parse_book_data(self, file, original_filename) -> BookFile:
        book_file = BookFile(file, original_filename, Mimetype.EPUB)
        book_file.title = self.title or original_filename
        book_file.description = self.description
        book_file.authors = list(self.authors) if self.authors else []
        book_file.tags = list(self.tags) if self.tags else []
        book_file.series_info = self.series_info
        book_file.language_code = self.language_code
        book_file.docdate = self.docdate or ""
        book_file.issues = list(self.issues) if self.issues else []
        return book_file
