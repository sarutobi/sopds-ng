# -*- coding: utf-8 -*-

import datetime
import logging
import os
import re
import time
import zipfile

from book_tools.format import create_bookfile
from opds_catalog import inpx_parser
from opds_catalog.config import catalog_config
from opds_catalog.constants import CAT_INP, CAT_INPX, CAT_NORMAL, CAT_ZIP
from opds_catalog.services import scanner
from opds_catalog.services.book_writer import BookWriter, FileSpec
from opds_catalog.services.inpx_adapter import to_book_metadata
from opds_catalog.services.raw_adapter import to_book_metadata_raw
from opds_catalog.utils import safe_log_str


class opdsScanner:
    def __init__(self, logger=None):
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger("scanner")
        self.writer = BookWriter(logger=self.logger)
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

    def _save_book_with_stats(self, meta, file_spec, cat, cat_type):
        """Внутренний метод для сохранения книги и обновления общей статистики."""
        try:
            outcome = self.writer.save_book(
                meta,
                file=file_spec,
                catalog=cat,
                cat_type=cat_type,
            )

            if outcome.created:
                self.books_added += 1
                if cat_type != CAT_NORMAL:
                    self.books_in_archives += 1
                self.logger.info(
                    f"Book {safe_log_str(file_spec.filename)} added to database."
                )
            else:
                self.books_skipped += 1
                self.logger.info(
                    f"Book {safe_log_str(file_spec.filename)} already in database."
                )
            return outcome
        except Exception as err:
            self.logger.error(
                f"Error saving book {safe_log_str(file_spec.filename)}: {err}"
            )
            self.bad_books += 1
            return None

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
                        self.logger.info(f"Process zip file {safe_log_str(file)}")
                        self.processzip(name, full_path, file)
                else:
                    self.logger.debug(f"Process regular file {safe_log_str(file)}")
                    file_size = os.path.getsize(file)
                    self.processfile(name, full_path, file, None, 0, file_size)

        self.books_deleted = scanner.books_del_phisical()

        self.log_stats()

    def _get_inp_rel_path(self, inpx_path: str, inp_name: str) -> str:
        """Единая точка расчета относительного пути для INP файла."""
        return os.path.relpath(
            os.path.join(inpx_path, inp_name), catalog_config.ROOT_LIB
        )

    def inpskip_callback(self, inpx, inp_file, inp_size) -> int:
        """Проверка необходимости обработки найденного inxp файла
        :inpx: найденный файл
        :inp_file:
        :inp_size: размер inp файла

        :returns: 0 если файл требуется обработать, 1 если обработка не требуется
        """
        rel_path = self._get_inp_rel_path(inpx, inp_file)

        if catalog_config.INPX_SKIP_UNCHANGED and scanner.archive_skip(
            rel_path, inp_size, depth=1
        ):
            self.logger.info(
                f"INP metafile {safe_log_str(inp_file)} not changed, skipping."
            )
            result = 1
        else:
            self.inp_cat = scanner.addcattree(rel_path, CAT_INPX, inp_size)
            self.logger.info(
                f"INP metafile {safe_log_str(inp_file)} stored as catalog {self.inp_cat}"
            )
            result = 0

        return result

    def inpx_callback(self, inpx, inp, meta_data, rel_path):
        self.logger.info(
            f"Append book {safe_log_str(meta_data[inpx_parser.sTitle])} to database"
        )

        rel_path_current = os.path.join(rel_path, meta_data[inpx_parser.sFolder])
        self.logger.debug(f"Library book path is {rel_path_current}")

        # Используем BookWriter вместо legacy scanner.findbook/addbook
        from opds_catalog.services.book_writer import FileSpec

        file_spec = FileSpec(
            path=rel_path_current,
            filename=meta_data[inpx_parser.sFile],
            rel_path=rel_path_current,
            extension=meta_data[inpx_parser.sExt],
            file_size=int(meta_data[inpx_parser.sSize])
            if meta_data[inpx_parser.sSize]
            else 0,
        )

        # Создаем метаданные через адаптер
        meta = to_book_metadata(meta_data, rel_path)

        # Создаем каталог для книги (в соответствии с legacy-логикой)
        cat = scanner.addcattree(rel_path_current, CAT_INP)

        # Сохраняем книгу и обновляем статистику
        self._save_book_with_stats(
            meta,
            file_spec=file_spec,
            cat=cat,
            cat_type=CAT_INP,
        )

    def processinpx(self, name, full_path, file):
        self.logger.info(f"Start processing INPX file {safe_log_str(name)}")
        self.logger.debug(f"Full path =  {safe_log_str(full_path)}")

        rel_file = os.path.relpath(file, catalog_config.ROOT_LIB)
        inpx_size = os.path.getsize(file)
        if catalog_config.INPX_SKIP_UNCHANGED and scanner.archive_skip(
            rel_file, inpx_size, depth=2
        ):
            self.logger.info(f"INPX file {safe_log_str(file)} is not changed. Skipping")
        else:
            self.logger.info(f"Create catalog for INPX file {safe_log_str(file)}")
            scanner.addcattree(rel_file, CAT_INPX, inpx_size)
            inpx = inpx_parser.Inpx(file, self.inpx_callback, self.inpskip_callback)
            # FIXME: Неизвестные атрибуты inpx_parser
            inpx.INPX_TEST_ZIP = catalog_config.INPX_TEST_ZIP
            inpx.INPX_TEST_FILES = catalog_config.INPX_TEST_FILES

            # Обертка для передачи rel_path в callback (Task 2.1)
            # Мы получаем rel_path из inpskip_callback, но Inpx.parse вызывает callback
            # с фиксированным числом аргументов. Чтобы передать rel_path,
            # мы можем либо использовать замыкание, либо модифицировать Inpx.parse.
            # Но проще всего — обернуть callback.

            # В Inpx.parse() вызывается append_callback(self.inpx_file, inp_name, meta_data)
            # Нам нужно добавить четвертый аргумент.
            # Поскольку we cannot easily change Inpx.parse without changing the class,
            # we will use a wrapper that gets the current rel_path.

            # Однако, в Inpx.parse() путь к текущему .inp файлу известен.
            # Чтобы избежать зависимости от мутируемого self.rel_path,
            # мы создаем локальный callback для каждого .inp файла.

            def wrapped_callback(inpx_file, inp_name, meta_data):
                # Вычисляем rel_path для текущего .inp файла через единую функцию
                current_rel_path = self._get_inp_rel_path(inpx_file, inp_name)
                return self.inpx_callback(
                    inpx_file, inp_name, meta_data, current_rel_path
                )

            inpx = inpx_parser.Inpx(file, wrapped_callback, self.inpskip_callback)
            inpx.INPX_TEST_ZIP = catalog_config.INPX_TEST_ZIP
            inpx.INPX_TEST_FILES = catalog_config.INPX_TEST_FILES
            inpx.parse()

    def processzip(self, name, full_path, file):
        self.logger.info(f"Start processing zipfile {safe_log_str(name)}")
        self.logger.debug(f"File directory: {safe_log_str(full_path)}")
        self.logger.debug(f"Full file path: {safe_log_str(file)}")
        rel_file = os.path.relpath(file, catalog_config.ROOT_LIB)
        zsize = os.path.getsize(file)
        if scanner.archive_skip(rel_file, zsize, depth=0):
            self.arch_skipped += 1
            self.logger.info(
                f"Skip ZIP archive {safe_log_str(rel_file)}. Already scanned."
            )
        else:
            # TODO:Обработка файлов в ФС должна быть описана в одном месте
            self.logger.info(f"Process ZIP archive {safe_log_str(rel_file)}")
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
        self.logger.info(f"Start processing file {safe_log_str(name)}")
        self.logger.debug(f"File directory: {safe_log_str(full_path)}")
        self.logger.debug(f"File path: {safe_log_str(file)}")
        self.logger.debug(f"Catalog type: {cat}")
        self.logger.debug(f"Archive: {archive}")
        self.logger.debug(f"File size: {file_size}")
        (n, e) = os.path.splitext(name)
        if e.lower() in catalog_config.BOOK_EXTENSIONS:
            rel_path = os.path.relpath(full_path, catalog_config.ROOT_LIB)
            self.logger.debug(
                f"Attempt to add book {safe_log_str(rel_path + '/' + name)}"
            )
            try:
                # Используем BookWriter для проверки существования книги
                # Мы создаем FileSpec для предварительной проверки
                file_spec = FileSpec(
                    path=rel_path,
                    filename=name,
                    rel_path=rel_path,
                    extension=e[1:],
                    file_size=file_size,
                )

                if self.writer.exists(file_spec):
                    self.books_skipped += 1
                    self.logger.info(
                        f"Book {safe_log_str(rel_path + '/' + name)} already in database."
                    )
                    return

                self.logger.info(f"Book {safe_log_str(name)} is new")
                if archive == 0:
                    self.logger.info(f"Add new catalog {safe_log_str(rel_path)}")
                    cat = scanner.addcattree(rel_path, archive)

                try:
                    self.logger.info(
                        f"Extracting book metadata from {safe_log_str(name)}"
                    )
                    book_data = create_bookfile(file, name)
                except Exception as err:
                    book_data = None
                    self.logger.error(
                        f"{safe_log_str(rel_path)} - {safe_log_str(name)} book parse error, skipping. Error was: {err}"
                    )
                    self.bad_books += 1

                if book_data:
                    # Преобразуем BookData в унифицированный BookMetadata через адаптер
                    meta = to_book_metadata_raw(book_data, name)

                    # Сохраняем книгу и обновляем статистику
                    self._save_book_with_stats(
                        meta,
                        file_spec=file_spec,
                        cat=cat,
                        cat_type=archive if archive != 0 else CAT_NORMAL,
                    )

            except UnicodeEncodeError as err:
                self.logger.error(
                    f"{rel_path} - {name} book UnicodeEncodeError error, skipping. Error was: {err}"
                )
                self.bad_books += 1
