from io import BytesIO

import pytest

from book_tools.format.bookfile import BookFile


class MockBookFile(BookFile):
    def __exit__(self, kind, value, traceback):
        pass


def test_book_file_protected_methods_access():
    with MockBookFile(BytesIO(b"test"), "test.epub", "application/epub+zip") as bf:
        bf._set_title("Test Title")
        bf._set_docdate("2023-01-01")
        bf._add_author("Author Name", "Name")
        bf._add_tag("Genre Tag")

        assert bf.title == "Test Title"
        assert bf.docdate == "2023-01-01"
        assert bf.authors == [{"name": "Author Name", "sortkey": "name"}]
        assert bf.tags == ["Genre Tag"]
