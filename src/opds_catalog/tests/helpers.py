# Helper functions for testing purpose
#

import io
import zipfile

from codecs import open

from opds_catalog import opdsdb
from opds_catalog.models import Book


def read_file_as_iobytes(file: str) -> io.BytesIO:
    """Чтение содержимого файла из файловой системы в BytesIO"""
    content = io.BytesIO()

    with open(file, "rb") as f:
        content.write(f.read())

    content.seek(0)
    return content


def read_book_from_zip_file(zip_file: str, bookname: str) -> io.BytesIO:
    """Чтение книги из zip архива"""
    content = io.BytesIO()

    with open(zip_file, "rb") as f:
        with zipfile.ZipFile(f, "r", allowZip64=True) as zf:
            with zf.open(bookname, "r") as book:
                content.write(book.read())

    content.seek(0)
    return content


class BookFactoryMixin:
    def setup_regular_book(self, filename="", path="") -> Book:
        """Генерирует книгу, размещенную в обычном файле в файловой системе"""
        return self.setup_book(filename=filename, cat_type=opdsdb.CAT_NORMAL, path=path)

    def setup_zipped_book(self, filename="", path="") -> Book:
        """Генерирует книгу, размещенную в zip файле в файловой системе"""
        return self.setup_book(filename=filename, cat_type=opdsdb.CAT_ZIP, path=path)

    def setup_book(self, title="", format="", filename="", cat_type=0, path="") -> Book:
        return Book(
            title=title, format=format, filename=filename, cat_type=cat_type, path=path
        )
