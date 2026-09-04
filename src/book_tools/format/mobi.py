import os
import shutil
from tempfile import mkdtemp

from book_tools.format.bookfile import BookFile
from book_tools.format.mimetype import Mimetype
from book_tools.pymobi.mobi import BookMobi


class Mobipocket(BookFile):
    def __init__(self, file, original_filename):
        BookFile.__init__(self, file, original_filename, Mimetype.MOBI)
        bm = BookMobi(file)
        self._encryption_method = bm["encryption"]
        self._set_title(bm["title"])
        self._add_author(bm["author"])
        docdate = bm["modificationDate"]
        if docdate:
            try:
                docdate_str = docdate.strftime("%Y-%m-%d")
            except (AttributeError, ValueError):
                docdate_str = ""
        else:
            docdate_str = ""
        self._set_docdate(docdate_str)
        if bm["subject"]:
            for tag in bm["subject"]:
                self._add_tag(tag)
        self.description: str = bm["description"]

    @classmethod
    def parse_book_data(cls, file, original_filename):
        book_file = BookFile(file, original_filename, Mimetype.MOBI)
        bm = BookMobi(file)
        book_file._set_title(bm["title"])
        book_file._add_author(bm["author"])
        docdate = bm["modificationDate"]
        if docdate:
            try:
                docdate_str = docdate.strftime("%Y-%m-%d")
            except (AttributeError, ValueError):
                docdate_str = ""
        else:
            docdate_str = ""
        book_file._set_docdate(docdate_str)
        if bm["subject"]:
            for tag in bm["subject"]:
                book_file._add_tag(tag)
        book_file.description = bm["description"]
        return book_file

    def __exit__(self, kind, value, traceback):
        pass

    def get_encryption_info(self):
        return (
            {"method": self._encryption_method}
            if self._encryption_method != "no encryption"
            else {}
        )

    def extract_cover_internal(self, working_dir):
        tmp_dir = mkdtemp(dir=working_dir)
        BookMobi(self.file).unpackMobi(tmp_dir + "/bookmobi")
        try:
            if os.path.isfile(tmp_dir + "/bookmobi_cover.jpg"):
                shutil.copy(tmp_dir + "/bookmobi_cover.jpg", working_dir)
                return ("bookmobi_cover.jpg", False)
            else:
                return (None, False)
        finally:
            shutil.rmtree(tmp_dir)

    def extract_cover_memory(self):
        try:
            image = BookMobi(self.file).unpackMobiCover()
        except Exception as err:
            print(err)
            image = None

        return image
