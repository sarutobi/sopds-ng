from io import BytesIO

from book_tools.format.mimetype import Mimetype
from book_tools.services import create_bookfile_service


def test_create_bookfile_service_fb2_zip_utf8():
    with open("tests/fixtures/fb2_utf8.zip.bin", "rb") as f:
        data = BytesIO(f.read())

    book_file = create_bookfile_service(data, "test_utf8.zip")

    assert book_file.title == "UTF8 Book"
    assert any(a["name"] == "Ivan Ivanov" for a in book_file.authors)
    assert book_file.mimetype == Mimetype.FB2


def test_create_bookfile_service_fb2_zip_cp1251():
    with open("tests/fixtures/fb2_cp1251.zip.bin", "rb") as f:
        data = BytesIO(f.read())

    book_file = create_bookfile_service(data, "test_cp1251.zip")

    assert book_file.title == "CP1251 Book"
    assert any(a["name"] == "Петр Петров" for a in book_file.authors)
    assert book_file.mimetype == Mimetype.FB2
