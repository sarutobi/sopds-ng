#######################################################################
#
# Вспомогательные функции
#
# import unicodedata

from django.conf import settings
import logging
import os
from opds_catalog import opdsdb
from opds_catalog.models import Book
from opds_catalog import utils
from constance import config
from io import BytesIO
import chardet
import zipfile
from zipfile import ZipInfo
import subprocess
import codecs

logger = logging.getLogger(__name__)

# Logger for scanner
scan_logger = logging.getLogger("scanner")


def translit(s: str) -> str:
    """Russian translit: converts 'привет'->'privet'"""
    assert s is not str, "Error: argument MUST be string"

    table1 = str.maketrans(
        "абвгдеёзийклмнопрстуфхъыьэАБВГДЕЁЗИЙКЛМНОПРСТУФХЪЫЬЭ",
        "abvgdeezijklmnoprstufh'y'eABVGDEEZIJKLMNOPRSTUFH'Y'E",
    )
    table2 = {
        "ж": "zh",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ю": "ju",
        "я": "ja",
        "Ж": "Zh",
        "Ц": "Ts",
        "Ч": "Ch",
        "Ш": "Sh",
        "Щ": "Sch",
        "Ю": "Ju",
        "Я": "Ja",
        "«": "",
        "»": "",
        '"': "",
        "\n": "_",
        " ": "_",
        "'": "",
        ":": "_",
        "№": "N",
    }
    s = s.translate(table1)
    for k in table2.keys():
        s = s.replace(k, table2[k])
    return s


def to_ascii(s):
    return s.encode("ascii", "replace").decode("utf-8")


def get_lang_name(lang: str) -> str:
    """Преобразование языкового кода в наименование языка"""
    k = lang.upper()
    if k in settings.LANGUAGE_NAMES.keys():
        return settings.LANGUAGE_NAMES[k]

    return lang


def getFileName(book: Book) -> str:
    """Формирует название файла для сохранения книги в латинице"""
    if config.SOPDS_TITLE_AS_FILENAME:
        transname = utils.translit(book.title + "." + book.format)
    else:
        transname = utils.translit(book.filename)

    return utils.to_ascii(transname)


def get_fs_book_path(book: Book) -> str:
    """Формирует полный путь в файловой системе библиотеки для файла книги"""
    logger.info(f"Create file path for book {book.id}")
    path = os.path.join(config.SOPDS_ROOT_LIB, book.path)
    if book.cat_type == opdsdb.CAT_INP:
        logger.info("Book has been placed in INP/INPX catalog")
        # Убираем из пути INPX и INP файл
        inp_path, zip_name = os.path.split(path)
        inpx_path, inp_name = os.path.split(inp_path)
        n_path, inpx_name = os.path.split(inpx_path)
        path = os.path.join(n_path, zip_name)

    logger.debug(f"Real book file path is {path}")
    return path


def read_from_regular_file(file_path: str) -> BytesIO | None:
    """Читает содержимое обычного файла из файловой системы"""

    logger.info(f"Reading content from {file_path} as regular file")
    if not os.path.isfile(file_path):
        logger.error(f"File {file_path} is not a regular file!")
        return None

    with open(file_path, "rb") as book:
        content = BytesIO(book.read())

    content.seek(0)
    logger.info(f"Readed {len(content.getvalue())} bytes from {file_path}")
    return content


def decode_string(string: str) -> str:
    """Определение кодировки и перекодирование строки
    :param string: Строка в неизвестной кодировке

    :return: Перекодированная в корректную коидировку строка
    """
    scan_logger.info("Detecting string encoding")
    detector = chardet.detect(string.encode("cp437"))
    encoding = detector.get("encoding") or "latin1"
    scan_logger.debug(f"Encoding: {encoding}")
    return string.encode("cp437").decode(encoding)


def read_from_zipped_file(zip_path: str, filename: str) -> BytesIO | None:
    """Читает содержимое файла filename из zip файла в файловой системе"""
    logger.info(f"Reading content of file {filename} from ZIP {zip_path}")
    if not os.path.isfile(zip_path):
        logger.error(f"File {zip_path} not found!")
        return None

    try:
        with open(zip_path, "rb") as zip:
            with zipfile.ZipFile(zip, "r", allowZip64=True) as zc:
                # TODO: Проверка существования нужного файла в архиве
                # issue 2 - если в архиве имя файла в некорректной кодировке,
                # то такой файл не получается извлечь из архива.
                for f in zc.infolist():
                    # Используем библиотеку chardet для определения кодировок имен файлов в ZIP
                    candidate = f.filename
                    decoded_filename = decode_string(candidate)
                    if decoded_filename == filename:
                        with zc.open(candidate, "r") as book:
                            content = BytesIO(book.read())
                            content.seek(0)
                            logger.debug(
                                f"Readed {len(content.getvalue())} bytes from {zip_path}"
                            )
                            return content
        logger.error(f"Cannot find file {filename} in ZIP archive {zip_path}")
        return None
    except KeyError as e:
        logger.error(
            f"Can not read file {filename} from ZIP archive {zip_path}: {e}"
        )
        return None


def getFileData(book: Book) -> BytesIO | None:
    """Поиск и считывание файла книги из ФС"""
    logger.info(f"Reading book file {book.filename} from file system")
    full_path = get_fs_book_path(book)
    logger.info(f"Read file from {full_path}")
    if book.cat_type == opdsdb.CAT_NORMAL:
        file_path = os.path.join(full_path, book.filename)
        logger.info(f"Reading file {book.filename} as regular file")
        return read_from_regular_file(file_path)

    elif book.cat_type in [opdsdb.CAT_ZIP, opdsdb.CAT_INP]:
        logger.info(f"Reading file {book.filename} from zipped catalog")
        return read_from_zipped_file(full_path, book.filename)


def getFileDataZip(book: Book) -> BytesIO:
    """Читает файл из ФС и упаковывает его в zip"""
    transname = getFileName(book)
    fo = getFileData(book)
    dio = BytesIO()
    if fo is not None:
        with zipfile.ZipFile(dio, "w", zipfile.ZIP_DEFLATED) as zo:
            zo.writestr(transname, fo.read())
        dio.seek(0)
    return dio


def getFileDataConv(book, convert_type):
    # TODO: необходимо настроить конверторы
    # TODO: дополнить тесты
    if book.format != "fb2":
        return None

    fo = getFileData(book)

    if not fo:
        return None

    transname = getFileName(book)

    (n, e) = os.path.splitext(transname)
    dlfilename = f"{n}.{convert_type}"

    if convert_type == "epub":
        converter_path = config.SOPDS_FB2TOEPUB
    elif convert_type == "mobi":
        converter_path = config.SOPDS_FB2TOMOBI
    else:
        fo.close()
        return None

    tmp_fb2_path = os.path.join(config.SOPDS_TEMP_DIR, book.filename)
    tmp_conv_path = os.path.join(config.SOPDS_TEMP_DIR, dlfilename)
    fw = open(tmp_fb2_path, "wb")
    fw.write(fo.read())
    fw.close()
    fo.close()

    popen_args = '"%s" "%s" "%s"' % (
        converter_path,
        tmp_fb2_path,
        tmp_conv_path,
    )
    proc = subprocess.Popen(popen_args, shell=True, stdout=subprocess.PIPE)
    # У следующий строки 2 функции 1-получение информации по конвертации и 2- ожидание конца конвертации
    # В силу 2й функции ее удаление приведет к ошибке выдачи сконвертированного файла
    out = proc.stdout.readlines()  # noqa: F841

    if not os.path.isfile(tmp_conv_path):
        return None

    fo = codecs.open(tmp_conv_path, "rb")

    dio = BytesIO(fo.read())
    # dio.write(fo.read())
    dio.seek(0)

    fo.close()
    os.remove(tmp_fb2_path)
    os.remove(tmp_conv_path)

    return dio


def getFileDataEpub(book):
    return getFileDataConv(book, "epub")


def getFileDataMobi(book):
    return getFileDataConv(book, "mobi")


def get_infolist_filename(
    infolist: list[ZipInfo], filename: str
) -> str | None:
    """Поиск имени файла в ZIP архиве.

        Кодировка имен файлов в ZIP архиве может быть отличной от UTF-8, из-за
        этого прямое чтение файла из архива может не сработать.
        Функция пытается определить кодировку имен файлов в архиве и найти
        нужное имя файла.

    :param infolist: Список файлов (infolist) ZIP архива.
    :type infolist: list[ZipInfo]
    :param filename: Имя файла, которое нужно найти в списке, в кодировке UTF-8
    :type filename: str
    :returns: Найденное в infolist имя файла в ZIP архиве. Если имя файла не найдено, то возвращается None.
    :rtype: str|None
    """

    fnames = [x.filename for x in infolist]
    # Fast check
    if filename in fnames:
        return filename

    # Decode check
    for candidate in fnames:
        decoded = decode_string(candidate)
        if decoded == filename:
            return candidate
    return None
