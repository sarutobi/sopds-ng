# -*- coding: utf-8 -*-
from book_tools.format.parsers import FB2

import os
import codecs

# import base64
import io
import subprocess

from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpRequest
# from django.views.decorators.cache import cache_page

from opds_catalog.models import Book, bookshelf
from opds_catalog import settings, utils, opdsdb  # , fb2parse

# import opds_catalog.zipf as zipfile
import zipfile

from book_tools.format import create_bookfile, mime_detector
from book_tools.format.mimetype import Mimetype

from constance import config
from PIL import Image

from opds_catalog.decorators import sopds_auth_validate


def getFileName(book: Book) -> str:
    """формирует название файла для сохранения книги в латинице"""
    if config.SOPDS_TITLE_AS_FILENAME:
        transname = utils.translit(book.title + "." + book.format)
    else:
        transname = utils.translit(book.filename)

    return utils.to_ascii(transname)


def get_fs_book_path(book: Book) -> str:
    """Формирует полный путь в файловой системе библиотеки для файла книги"""
    path = os.path.join(config.SOPDS_ROOT_LIB, book.path)
    if book.cat_type == opdsdb.CAT_INP:
        # Убираем из пути INPX и INP файл
        inp_path, zip_name = os.path.split(path)
        inpx_path, inp_name = os.path.split(inp_path)
        n_path, inpx_name = os.path.split(inpx_path)
        return os.path.join(n_path, zip_name)
    else:
        return path


def read_from_regular_file(file_path: str) -> io.BytesIO | None:
    """Читает содержимое обычного файла из файловой системы"""

    if not os.path.isfile(file_path):
        # TODO залоггировать ошибку
        return None

    content = io.BytesIO()
    with open(file_path, "rb") as book:
        content.write(book.read())

    content.seek(0)
    return content


def read_from_zipped_file(zip_path: str, filename: str) -> io.BytesIO | None:
    """Читает содержимое файла filename из zip файла в файловой системе"""

    if not os.path.isfile(zip_path):
        # TODO: залоггировать ошибку
        return None

    content = io.BytesIO()
    try:
        with open(zip_path, "rb") as zip:
            with zipfile.ZipFile(zip, "r", allowZip64=True) as zc:
                # TODO Проверка существования нужного файла в архиве
                with zc.open(filename, "r") as book:
                    content.write(book.read())

        content.seek(0)
        return content
    except KeyError:
        # TODO Залоггировать ошибку
        return None


def getFileData(book: Book) -> io.BytesIO | None:
    """Поиск и считывание файла книги из ФС"""
    full_path = get_fs_book_path(book)

    if book.cat_type == opdsdb.CAT_NORMAL:
        file_path = os.path.join(full_path, book.filename)
        return read_from_regular_file(file_path)

    elif book.cat_type in [opdsdb.CAT_ZIP, opdsdb.CAT_INP]:
        return read_from_zipped_file(full_path, book.filename)


def getFileDataZip(book: Book) -> io.BytesIO:
    """Читает файл из ФС и упаковывает его в zip"""
    transname = getFileName(book)
    fo = getFileData(book)
    dio = io.BytesIO()
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
    dlfilename = "%s.%s" % (n, convert_type)

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

    popen_args = '"%s" "%s" "%s"' % (converter_path, tmp_fb2_path, tmp_conv_path)
    proc = subprocess.Popen(popen_args, shell=True, stdout=subprocess.PIPE)
    # У следующий строки 2 функции 1-получение информации по конвертации и 2- ожидание конца конвертации
    # В силу 2й функции ее удаление приведет к ошибке выдачи сконвертированного файла
    out = proc.stdout.readlines()  # noqa: F841

    if os.path.isfile(tmp_conv_path):
        fo = codecs.open(tmp_conv_path, "rb")
    else:
        return None

    dio = io.BytesIO()
    dio.write(fo.read())
    dio.seek(0)

    fo.close()
    os.remove(tmp_fb2_path)
    os.remove(tmp_conv_path)

    return dio


def getFileDataEpub(book):
    return getFileDataConv(book, "epub")


def getFileDataMobi(book):
    return getFileDataConv(book, "mobi")


@sopds_auth_validate
def Download(request, book_id, zip_flag):
    # TODO: это view, он должен быть в другом месте
    # TODO: реорганизовать в части формирования ответа
    """Загрузка файла книги"""
    book = Book.objects.get(id=book_id)

    if config.SOPDS_AUTH:
        #        if not request.user.is_authenticated:
        #            bau = BasicAuthMiddleware()
        #            request = bau.process_request(request)
        #            if not hasattr(request, "user"):
        #                return request

        if request.user.is_authenticated:
            bookshelf.objects.get_or_create(user=request.user, book=book)

    transname = getFileName(book)
    transname = utils.to_ascii(transname)

    if zip_flag == "1":
        dlfilename = transname + ".zip"
        content_type = Mimetype.FB2_ZIP if book.format == "fb2" else Mimetype.ZIP
    else:
        dlfilename = transname
        content_type = mime_detector.fmt(book.format)

    response = HttpResponse()
    response["Content-Type"] = '%s; name="%s"' % (content_type, dlfilename)
    response["Content-Disposition"] = 'attachment; filename="%s"' % (dlfilename)
    response["Content-Transfer-Encoding"] = "binary"

    s = getFileData(book)

    if zip_flag == "1":
        dio = io.BytesIO()
        with zipfile.ZipFile(dio, "w", zipfile.ZIP_DEFLATED) as zo:
            zo.writestr(transname, s.getvalue())

        response["Content-Length"] = str(dio.getbuffer().nbytes)
        response.write(dio)
    else:
        response["Content-Length"] = str(s.getbuffer().nbytes)
        response.write(s)

    return response


# Новая версия (0.42) процедуры извлечения обложек из файлов книг fb2, epub, mobi
# @cache_page(config.SOPDS_CACHE_TIME)
def Cover(
    request: HttpRequest, book_id: int, thumbnail=False
) -> HttpResponse | HttpResponseRedirect:
    # FIXME: Это view, он должен находиться в другом файле
    """
    Загрузка обложки

    Args:
        request(HttpRequest): поступивший django запрос

        book_id(int): идентификатор книги

        thumbnail(bool): требуется ли создавать превью обложки

    Returns:
       HttpResponse: изображение обложки, если обложка была найдена в книге
       HttpResponseRedirect: ссылка на стандартную обложку, если обложка не бла найдена в книге
    """
    book = Book.objects.get(id=book_id)
    response = HttpResponse()
    # full_path = get_fs_book_path(book)

    try:
        if book.format == "fb2":
            content = getFileData(book)
            assert content is not None
            parser = FB2(content, book.filename, Mimetype.FB2)
            image = parser.extract_cover()
        else:
            book_data = create_bookfile(getFileData(book), book.filename)
            image = book_data.extract_cover_memory()
    except Exception as e:
        book_data = None
        image = None

    if image:
        response["Content-Type"] = "image/jpeg"
        if thumbnail:
            thumb = Image.open(io.BytesIO(image)).convert("RGB")
            thumb.thumbnail((settings.THUMB_SIZE, settings.THUMB_SIZE), Image.LANCZOS)
            tfile = io.BytesIO()
            thumb.save(tfile, "JPEG")
            image = tfile.getvalue()
        response.write(image)

    if not image:
        # Вместо обработки изображения отдаем ссылку на изображение "Нет обложки"
        return HttpResponseRedirect(config.SOPDS_NOCOVER_PATH)

    return response


def Thumbnail(request, book_id):
    return Cover(request, book_id, True)


def ConvertFB2(request, book_id, convert_type):
    """Выдача файла книги после конвертации в EPUB или mobi"""
    book = Book.objects.get(id=book_id)

    if book.format != "fb2":
        raise Http404

    if config.SOPDS_AUTH and request.user.is_authenticated:
        bookshelf.objects.get_or_create(user=request.user, book=book)

    full_path = os.path.join(config.SOPDS_ROOT_LIB, book.path)
    if book.cat_type == opdsdb.CAT_INP:
        # Убираем из пути INPX и INP файл
        inp_path, zip_name = os.path.split(full_path)
        inpx_path, inp_name = os.path.split(inp_path)
        path, inpx_name = os.path.split(inpx_path)
        full_path = os.path.join(path, zip_name)

    if config.SOPDS_TITLE_AS_FILENAME:
        transname = utils.translit(book.title + "." + book.format)
    else:
        transname = utils.translit(book.filename)

    transname = utils.to_ascii(transname)

    (n, e) = os.path.splitext(transname)
    dlfilename = "%s.%s" % (n, convert_type)

    if convert_type == "epub":
        converter_path = config.SOPDS_FB2TOEPUB
    elif convert_type == "mobi":
        converter_path = config.SOPDS_FB2TOMOBI
    content_type = mime_detector.fmt(convert_type)

    if book.cat_type == opdsdb.CAT_NORMAL:
        tmp_fb2_path = None
        file_path = os.path.join(full_path, book.filename)
    elif book.cat_type in [opdsdb.CAT_ZIP, opdsdb.CAT_INP]:
        try:
            fz = codecs.open(full_path, "rb")
        except FileNotFoundError:
            raise Http404
        z = zipfile.ZipFile(fz, "r", allowZip64=True)
        z.extract(book.filename, config.SOPDS_TEMP_DIR)
        tmp_fb2_path = os.path.join(config.SOPDS_TEMP_DIR, book.filename)
        file_path = tmp_fb2_path

    tmp_conv_path = os.path.join(config.SOPDS_TEMP_DIR, dlfilename)
    popen_args = '"%s" "%s" "%s"' % (converter_path, file_path, tmp_conv_path)
    proc = subprocess.Popen(popen_args, shell=True, stdout=subprocess.PIPE)
    # proc = subprocess.Popen((converter_path.encode('utf8'),file_path.encode('utf8'),tmp_conv_path.encode('utf8')), shell=True, stdout=subprocess.PIPE)
    out = proc.stdout.readlines()  # noqa: F841

    if os.path.isfile(tmp_conv_path):
        fo = codecs.open(tmp_conv_path, "rb")
        s = fo.read()
        # HTTP Header
        response = HttpResponse()
        response["Content-Type"] = '%s; name="%s"' % (content_type, dlfilename)
        response["Content-Disposition"] = 'attachment; filename="%s"' % (dlfilename)
        response["Content-Transfer-Encoding"] = "binary"
        response["Content-Length"] = str(len(s))
        response.write(s)
        fo.close()
    else:
        raise Http404

    try:
        if tmp_fb2_path:
            os.remove(tmp_fb2_path)
    except:
        pass
    try:
        os.remove(tmp_conv_path)
    except:
        pass

    return response
