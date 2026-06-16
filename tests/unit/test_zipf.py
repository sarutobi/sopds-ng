import os
import zipfile


ROOT_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "data")
TEST_ZIP = "books.zip"
TEST_BAD_ZIP = "badfile.zip"


class TestZip:  # unit
    """Тесты для работы с zip-архивами."""

    def test_zip_valid(self) -> None:
        z = zipfile.ZipFile(os.path.join(ROOT_LIB, TEST_ZIP), "r", allowZip64=True)
        filelist = z.namelist()
        file_size = z.getinfo("539485.fb2").file_size
        file = z.open("539485.fb2")
        assert filelist == ["539603.fb2", "539485.fb2", "539273.fb2"]
        assert file_size == 12293
        assert file.read(38) == b'<?xml version="1.0" encoding="utf-8"?>'
        file.close()

    def test_zip_novalid(self) -> None:
        bad_file_count = 0
        try:
            zipfile.ZipFile(os.path.join(ROOT_LIB, TEST_BAD_ZIP), "r", allowZip64=True)
        except zipfile.BadZipFile:
            bad_file_count = 1

        assert bad_file_count == 1
