"""Команда поиска дубликатов книг.

Использует единый сервис DuplicatesService для обнаружения
дубликатов по всей коллекции. Логика определения дублей
изолирована в одном месте и в дальнейшем может быть вынесена
в плагин (Release 2.0).
"""

import logging
import os

from django.conf import settings as main_settings
from django.core.management.base import BaseCommand

from opds_catalog import settings
from opds_catalog.config import catalog_config
from opds_catalog.services.duplicates_service import DuplicatesService


class Command(BaseCommand):
    help = "Find book duplicates"
    scan_is_active = False

    def add_arguments(self, parser):
        parser.add_argument("command", help="Use start ")
        parser.add_argument(
            "--verbose",
            action="store_true",
            dest="verbose",
            default=False,
            help="Set verbosity level for books duplicates checker.",
        )

    def handle(self, *args, **options):
        self.pidfile = os.path.join(
            main_settings.BASE_DIR, catalog_config.SCANNER_PID_FILE
        )
        action = options["command"]
        self.logger = logging.getLogger("")
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")

        if settings.LOGLEVEL != logging.NOTSET:
            fh = logging.FileHandler(catalog_config.SCANNER_LOG_FILE)
            fh.setLevel(settings.LOGLEVEL)
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

        if options["verbose"]:
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

        if action == "start":
            self.stdout.write("Startup once book duplicates scan.")
            if self.scan_is_active:
                self.stdout.write("Scan process already active. Skip current job.")
                return

            self.scan_is_active = True

            # Используем единый сервис для поиска дубликатов.
            duplicates_map = DuplicatesService.find_all_duplicates()

            total_books_with_doubles = len(duplicates_map)
            self.logger.info(f"Found duplicates for {total_books_with_doubles} books")

            for book_id, doubles_qs in duplicates_map.items():
                self.logger.info(f"Book id={book_id} has doubles:")
                for dbl in doubles_qs:
                    self.logger.info(f"  - duplicate id={dbl.id}")

            self.scan_is_active = False
            self.stdout.write("Complete book duplicates scan.")
