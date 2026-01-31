# Helper functions for testing purpose
#

from io import BytesIO
import zipfile

# from codecs import open

from opds_catalog import opdsdb
from opds_catalog.models import Book, Catalog


def read_file_as_iobytes(file: str) -> BytesIO:
    """Чтение содержимого файла из файловой системы в BytesIO"""

    with open(file, "rb") as f:
        content = BytesIO(f.read())

    content.seek(0)
    return content


def read_book_from_zip_file(zip_file: str, bookname: str) -> BytesIO:
    """Чтение книги из zip архива"""

    with open(zip_file, "rb") as f:
        with zipfile.ZipFile(f, "r", allowZip64=True) as zf:
            with zf.open(bookname, "r") as book:
                content = BytesIO(book.read())

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


def create_catalog(
    cat_name: str = "Test catalog",
    path: str = "test_path",
) -> Catalog:
    catalog = Catalog(cat_name=cat_name, path=path)
    catalog.save()
    return catalog


def create_book(
    filename: str = "test_book",
    path: str = "test_path",
    filesize: int = 0,
    format: str = "fb2",
    catalog: str = "test_catalog",
    cat_type: int = opdsdb.CAT_NORMAL,
    doc_date: str = "2025-01-01 00:00:00",
    lang: str = "ru",
    title: str = "Test Book",
    annotation: str = "Lorem ipsum dolor sit....",
    lang_code: int = 2,
    avail: int = 2,
) -> Book:
    cat = create_catalog(catalog, path)

    book = Book(
        filename=filename,
        path=path,
        filesize=filesize,
        format=format,
        catalog=cat,
        cat_type=cat_type,
        docdate=doc_date,
        lang=lang,
        title=title,
        search_title=title.upper(),
        annotation=annotation,
        lang_code=lang_code,
        avail=avail,
    )
    book.save()
    return book
