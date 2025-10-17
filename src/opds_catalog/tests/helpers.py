# Helper functions for testing purpose
#

import io
import zipfile

from codecs import open


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
