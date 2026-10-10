# -*- coding: utf-8 -*-

import datetime
import logging
import os
import re
import time
import zipfile

from django.utils.translation import gettext as _

from book_tools.format import create_bookfile
from book_tools.format.util import strip_symbols
from opds_catalog import inpx_parser
from opds_catalog.config import catalog_config
from opds_catalog.constants import CAT_INP, CAT_INPX, CAT_ZIP
from opds_catalog.services import scanner


class opdsScanner:
    def __init__(self, logger=None):
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger("scanner")
        self.init_stats()

    def init_stats(self) -> None:
        """Сброс статистических параметров"""
        self.t1 = datetime.timedelta(seconds=time.time())
        self.t2 = self.t1
        self.t3 = self.t1
        self.books_added = 0
        self.books_skipped = 0
        self.books_deleted = 0
        self.arch_scanned = 0
        self.arch_skipped = 0
        self.bad_archives = 0
        self.bad_books = 0
        self.books_in_archives = 0

    def log_options(self) -> None:
        """Вывод в лог параметров контекста запуска сканера"""
        # TODO: Вынести это в вызывающий код
        self.logger.info(" ***** Starting sopds-scan...")
        self.logger.debug("OPTIONS SET")
        if catalog_config.ROOT_LIB is not None:
            self.logger.debug(f"root_lib = {catalog_config.ROOT_LIB}")
        if catalog_config.FB2_TO_EPUB_PATH is not None:
            self.logger.debug(f"fb2toepub = {catalog_config.FB2_TO_EPUB_PATH}")
        if catalog_config.FB2_TO_MOBI_PATH is not None:
            self.logger.debug(f"fb2tomobi = {catalog_config.FB2_TO_MOBI_PATH}")
        if catalog_config.TEMP_DIR is not None:
            self.logger.debug(f"temp_dir = {catalog_config.TEMP_DIR}")

    def log_stats(self) -> None:
        """Вывод в лог статистики работы сканера"""
        # TODO: Вынести это в вызывающий код
        self.t2 = datetime.timedelta(seconds=time.time())
        self.logger.info("Books added      : " + str(self.books_added))
        self.logger.info("Books skipped    : " + str(self.books_skipped))
        self.logger.info("Bad books        : " + str(self.bad_books))
        if catalog_config.DELETE_LOGICAL:
            self.logger.info("Books deleted    : " + str(self.books_deleted))
        else:
            self.logger.info("Books DB entries deleted : " + str(self.books_deleted))
        self.logger.info("Books in archives: " + str(self.books_in_archives))
        self.logger.info("Archives scanned : " + str(self.arch_scanned))
        self.logger.info("Archives skipped : " + str(self.arch_skipped))
        self.logger.info("Bad archives     : " + str(self.bad_archives))

        t = self.t2 - self.t1
        seconds = t.seconds % 60
        minutes = ((t.seconds - seconds) // 60) % 60
        hours = t.seconds // 3600
        self.logger.info(
            "Time estimated:"
            + str(hours)
            + " hours, "
            + str(minutes)
            + " minutes, "
            + str(seconds)
            + " seconds."
        )

    def scan_all(self):
        """Запуск сканирования библиотеки"""
        self.init_stats()
        self.log_options()
        self.inp_cat = None
        self.zip_file = None
        self.rel_path = None

        scanner.avail_check_prepare()
        self.logger.debug(f"ZipScan: {catalog_config.ZIP_SCAN_ENABLED}")
        for full_path, dirs, files in os.walk(
            catalog_config.ROOT_LIB, followlinks=True
        ):
            # Если разрешена обработка inpx, то при нахождении inpx обрабатываем его и прекращаем обработку текущего каталога
            if catalog_config.INPX_ENABLED:
                inpx_files = [
                    inpx for inpx in files if re.match(".*(.inpx|.INPX)$", inpx)
                ]
                # Пропускаем обработку файлов в текущем каталоге, если найдены inpx
                if inpx_files:
                    for inpx_file in inpx_files:
                        file = os.path.join(full_path, inpx_file)
                        self.processinpx(inpx_file, full_path, file)
                    continue

            for name in files:
                file = os.path.join(full_path, name)
                (n, e) = os.path.splitext(name)
                if e.lower() == ".zip":
                    if catalog_config.ZIP_SCAN_ENABLED:
                        self.logger.info(f"Process zip file {file}")
                        self.processzip(name, full_path, file)
                else:
                    self.logger.info("Process regular file {file}")
                    file_size = os.path.getsize(file)
                    self.processfile(name, full_path, file, None, 0, file_size)

        self.books_deleted = scanner.books_del_phisical()

        self.log_stats()

    def inpskip_callback(self, inpx, inp_file, inp_size) -> int:
        """Проверка необходимости обработки найденного inxp файла
        :inpx: найденный файл
        :inp_file:
        :inp_size: размер inp файла

        :returns: 0 если файл требуется обработать, 1 если обработка не требуется
        """
        self.rel_path = os.path.relpath(
            os.path.join(inpx, inp_file), catalog_config.ROOT_LIB
        )

        if catalog_config.INPX_SKIP_UNCHANGED and scanner.archive_skip(
            self.rel_path, inp_size, depth=1
        ):
            self.logger.info(f"INP metafile {inp_file} not changed, skipping.")
            result = 1
        else:
            self.inp_cat = scanner.addcattree(self.rel_path, CAT_INPX, inp_size)
            self.logger.info(
                f"INP metafile {inp_file} stored as catalog {self.inp_cat}"
            )
            result = 0

        return result

    def inpx_callback(self, inpx, inp, meta_data):
        self.logger.info(f"Append book {meta_data[inpx_parser.sTitle]} to database")
        name = "%s.%s" % (
            meta_data[inpx_parser.sFile],
            meta_data[inpx_parser.sExt],
        )

        lang = meta_data[inpx_parser.sLang].strip(strip_symbols)
        title = meta_data[inpx_parser.sTitle].strip(strip_symbols)
        annotation = ""
        docdate = meta_data[inpx_parser.sDate].strip(strip_symbols)

        rel_path_current = os.path.join(self.rel_path, meta_data[inpx_parser.sFolder])
        self.logger.debug(f"Library book path is {rel_path_current}")
        if scanner.findbook(name, rel_path_current, 1) is None:
            self.logger.info(f"Book {name} is new, store to database")
            cat = scanner.addcattree(rel_path_current, CAT_INP)
            book = scanner.addbook(
                name,
                rel_path_current,
                cat,
                meta_data[inpx_parser.sExt],
                title,
                annotation,
                docdate,
                lang,
                meta_data[inpx_parser.sSize],
                CAT_INP,
            )
            self.books_added += 1
            self.books_in_archives += 1
            self.logger.debug("Book " + rel_path_current + "/" + name + " Added ok.")

            for a in set(meta_data[inpx_parser.sAuthor]):
                author = scanner.addauthor(a.replace(",", " "))
                scanner.addbauthor(book, author)

            for g in set(meta_data[inpx_parser.sGenre]):
                scanner.addbgenre(
                    book, scanner.addgenre(g.lower().strip(strip_symbols))
                )

            for s in set(meta_data[inpx_parser.sSeries]):
                ser = scanner.addseries(s.strip())
                scanner.addbseries(book, ser, 0)

    def processinpx(self, name, full_path, file):
        self.logger.info(f"Start processing INPX file {name}")
        self.logger.debug(f"Full path =  {full_path}")

        rel_file = os.path.relpath(file, catalog_config.ROOT_LIB)
        inpx_size = os.path.getsize(file)
        if catalog_config.INPX_SKIP_UNCHANGED and scanner.archive_skip(
            rel_file, inpx_size, depth=2
        ):
            self.logger.info(f"INPX file {file} is not changed. Skipping")
        else:
            self.logger.info(f"Create catalog for INPX file {file}")
            scanner.addcattree(rel_file, CAT_INPX, inpx_size)
            inpx = inpx_parser.Inpx(file, self.inpx_callback, self.inpskip_callback)
            # FIXME: Неизвестные атрибуты inpx_parser
            inpx.INPX_TEST_ZIP = catalog_config.INPX_TEST_ZIP
            inpx.INPX_TEST_FILES = catalog_config.INPX_TEST_FILES
            inpx.parse()

    def processzip(self, name, full_path, file):
        self.logger.info(f"Start processing zipfile {name}")
        self.logger.debug(f"File directory: {full_path}")
        self.logger.debug(f"Full file path: {file}")
        rel_file = os.path.relpath(file, catalog_config.ROOT_LIB)
        zsize = os.path.getsize(file)
        if scanner.archive_skip(rel_file, zsize, depth=0):
            self.arch_skipped += 1
            self.logger.info(f"Skip ZIP archive {rel_file}. Already scanned.")
        else:
            # TODO:Обработка файлов в ФС должна быть описана в одном месте
            self.logger.info(f"Process ZIP archive {rel_file}")
            zip_process_error = 0
            try:
                z = zipfile.ZipFile(file, "r", allowZip64=True)
                filelist = z.namelist()
                cat = scanner.addcattree(rel_file, CAT_ZIP, zsize)
                for n in filelist:
                    try:
                        file_size = z.getinfo(n).file_size
                        bookfile = z.open(n)
                        self.processfile(n, file, bookfile, cat, CAT_ZIP, file_size)
                        bookfile.close()
                    except zipfile.BadZipFile as e:
                        self.logger.warning(
                            f"Error processing  book file '{n}' in ZIP file '{file}': {e}"
                        )
                        zip_process_error = 1
                z.close()
                self.arch_scanned += 1
            except zipfile.BadZipFile as e:
                self.logger.error(
                    f"Error while read ZIP archive. File {file} corrupt: {e}"
                )
                zip_process_error = 1
            self.bad_archives += zip_process_error

    def processfile(self, name, full_path, file, cat, archive=0, file_size=0):
        self.logger.info(f"Start processing file {name}")
        self.logger.debug(f"File directory: {full_path}")
        self.logger.debug(f"File path: {file}")
        self.logger.debug(f"Catalog type: {cat}")
        self.logger.debug(f"Archive: {archive}")
        self.logger.debug(f"File size: {file_size}")
        (n, e) = os.path.splitext(name)
        if e.lower() in catalog_config.BOOK_EXTENSIONS:
            rel_path = os.path.relpath(full_path, catalog_config.ROOT_LIB)
            self.logger.debug(f"Attempt to add book {rel_path}/{name}")
            try:
                if scanner.findbook(name, rel_path, 1) is None:
                    self.logger.info(f"Book {name} is new")
                    if archive == 0:
                        self.logger.info(f"Add new catalog {rel_path}")
                        cat = scanner.addcattree(rel_path, archive)

                    try:
                        self.logger.info(f"Extracting book metadata from {name}")
                        book_data = create_bookfile(file, name)
                    except Exception as err:
                        book_data = None
                        self.logger.error(
                            f"{rel_path} - {name} book parse error, skipping. Error was: {err}"
                        )
                        self.bad_books += 1

                    # TODO: объект BookData должен сам выполнять валидацию своих полей при создании
                    if book_data:
                        lang = (
                            book_data.language_code.strip(strip_symbols)
                            if book_data.language_code
                            else ""
                        )
                        title = (
                            book_data.title.strip(strip_symbols)
                            if book_data.title
                            else n
                        )
                        annotation = book_data.description or ""
                        annotation = (
                            annotation.strip(strip_symbols)
                            if isinstance(annotation, str)
                            else annotation.decode("utf8").strip(strip_symbols)
                        )
                        docdate = book_data.docdate or ""

                        self.logger.info(f"Store book '{name}' metainfo in database")
                        book = scanner.addbook(
                            name,
                            rel_path,
                            cat,
                            e[1:],
                            title,
                            annotation,
                            docdate,
                            lang,
                            file_size,
                            archive,
                        )
                        self.books_added += 1

                        if archive != 0:
                            self.books_in_archives += 1
                        self.logger.info(
                            f"Book {rel_path}/{name}  metadata successfully writed to database."
                        )

                        self.logger.info(
                            f"Store authors metadata for {name} in database"
                        )
                        # Дедупликация авторов (список словарей)
                        seen_authors = []
                        for a in book_data.authors:
                            author_name = a.get("name", _("Unknown author")).strip(
                                strip_symbols
                            )
                            # Если в имени автора нет запятой, то фамилию переносим из конца в начало
                            if author_name and author_name.find(",") < 0:
                                author_names = author_name.split()
                                author_name = " ".join(
                                    [
                                        author_names[-1],
                                        " ".join(author_names[:-1]),
                                    ]
                                )
                            if author_name not in seen_authors:
                                seen_authors.append(author_name)
                                author = scanner.addauthor(author_name)
                                scanner.addbauthor(book, author)
                        self.logger.info("Authors metadata stored succesfully")

                        self.logger.info(
                            f"Store genres metadata for {name} in database"
                        )
                        for genre in set(book_data.tags):
                            scanner.addbgenre(
                                book,
                                scanner.addgenre(genre.lower().strip(strip_symbols)),
                            )
                        self.logger.info("Genres metadata stored successfully")

                        # FIXME: series_info определяется только по наличию названия серии, номер в серии устанавливается в 0 если не указан
                        if book_data.series_info:
                            ser = scanner.addseries(book_data.series_info["title"])
                            ser_no = book_data.series_info["index"] or "0"
                            ser_no = int(ser_no) if ser_no.isdigit() else 0
                            scanner.addbseries(book, ser, ser_no)
                else:
                    self.books_skipped += 1
                    self.logger.info(f"Book {rel_path}/{name} already in database.")
            except UnicodeEncodeError as err:
                self.logger.error(
                    f"{rel_path} - {name} book UnicodeEncodeError error, skipping. Error was: {err}"
                )
                self.bad_books += 1
