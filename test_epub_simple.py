import os
import sys
import zipfile
from io import BytesIO

# Добавляем src в путь для импорта
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    from book_tools.format.epub import EPub
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)


def test_epub_broken_zip():
    print("Testing broken zip...")
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")

    data = buf.getvalue()
    # Портим данные в конце файла, чтобы testzip() обнаружил ошибку CRC/структуры
    broken_data = data[:-5] + b"\xff\xff\xff\xff\xff"
    broken_buf = BytesIO(broken_data)

    try:
        EPub(broken_buf, "broken.epub")
        print("FAIL: Should have raised StructureException")
    except EPub.StructureException as e:
        print(f"SUCCESS: Caught expected exception: {e}")
    except Exception as e:
        print(f"FAIL: Caught unexpected exception: {type(e).__name__}: {e}")


if __name__ == "__main__":
    test_epub_broken_zip()
