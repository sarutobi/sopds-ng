import zipfile
from io import BytesIO

import pytest

from book_tools.format.epub import EPub


def test_epub_broken_zip():
    # Создаем минимальный валидный zip
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")

    data = buf.getvalue()
    # Портим данные в конце файла, чтобы testzip() обнаружил ошибку CRC/структуры
    broken_data = data[:-5] + b"\xff\xff\xff\xff\xff"
    broken_buf = BytesIO(broken_data)

    with pytest.raises(EPub.StructureException) as excinfo:
        EPub(broken_buf, "broken.epub")
    assert "broken zip archive" in str(excinfo.value)
