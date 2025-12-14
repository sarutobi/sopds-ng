# import PythonMagick
# from PIL import Image, ImageFile
import re

strip_symbols = " »«'\"&\n-.#\\`"


def list_zip_file_infos(zipfile):
    return [info for info in zipfile.infolist() if not info.filename.endswith("/")]


def normalize_string(text: str) -> str | None:
    """Убирает повторяющиеся пробелы и переносы строки во входной строке"""
    if text is None:
        return None
    return re.sub(r"\s+", " ", text.strip())


def minify_cover(path):
    # try:
    #     try:
    #         image = Image.open(path).convert('RGB')
    #     except:
    #         magick_image = PythonMagick.Image(path + '[0]')
    #         magick_image.write(path)
    #         image = Image.open(path).convert('RGB')
    #     width = image.size[0]
    #     if width > 600:
    #         new_width = 500
    #         new_height = int(float(new_width) * image.size[1] / width)
    #         image.thumbnail((new_width, new_height), Image.ANTIALIAS)
    #     ImageFile.MAXBLOCK = image.size[0] * image.size[1]
    #     image.save(path, 'JPEG', optimize=True, progressive=True)
    # except:
    #     pass
    pass
