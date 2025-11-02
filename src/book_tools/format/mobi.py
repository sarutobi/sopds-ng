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
        self.__set_title__(bm["title"])
        self.__add_author__(bm["author"])
        self.__set_docdate__(bm["modificationDate"].strftime("%Y-%m-%d"))
        if bm["subject"]:
            for tag in bm["subject"]:
                self.__add_tag__(tag)
        self.description: str = bm["description"]

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


class Mobipocket_new(object):
    def __init__(self, file, original_filename):
        # BookFile.__init__(self, file, original_filename, Mimetype.MOBI)
        bm = BookMobi(file)
        self._encryption_method = bm["encryption"]
        # self.__set_title__(bm["title"])
        # self.__add_author__(bm["author"])
        # self.__set_docdate__(bm["modificationDate"].strftime("%Y-%m-%d"))
        # if bm["subject"]:
        #     for tag in bm["subject"]:
        #         self.__add_tag__(tag)
        # self.description = bm["description"]

    def __exit__(self, kind, value, traceback):
        pass

    def parse_book_data(self, file, original_filename):
        book_file = BookFile(file, original_filename, Mimetype.MOBI)
        bm = BookMobi(file)
        self._encryption_method = bm["encryption"]
        book_file.__set_title__(bm["title"])
        book_file.__add_author__(bm["author"])
        book_file.__set_docdate__(bm["modificationDate"].strftime("%Y-%m-%d"))
        if bm["subject"]:
            for tag in bm["subject"]:
                book_file.__add_tag__(tag)
        book_file.description = bm["description"]
        return book_file

    def get_encryption_info(self):
        return (
            {"method": self._encryption_method}
            if self._encryption_method != "no encryption"
            else {}
        )

    def extract_cover_internal(self, file, working_dir):
        tmp_dir = mkdtemp(dir=working_dir)
        BookMobi(file).unpackMobi(tmp_dir + "/bookmobi")
        try:
            if os.path.isfile(tmp_dir + "/bookmobi_cover.jpg"):
                shutil.copy(tmp_dir + "/bookmobi_cover.jpg", working_dir)
                return ("bookmobi_cover.jpg", False)
            else:
                return (None, False)
        finally:
            shutil.rmtree(tmp_dir)

    def extract_cover_memory(self, file):
        try:
            image = BookMobi(file).unpackMobiCover()
        except Exception as err:
            print(err)
            image = None

        return image
