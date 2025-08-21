import os
import logging


from django.core.management.base import BaseCommand
from django.conf import settings as main_settings

from opds_catalog import settings 
from constance import config
from opds_catalog.models import Book

class Command(BaseCommand):
    help = 'Find book duplicates'
    scan_is_active = False

    def add_arguments(self, parser):
        parser.add_argument('command', help='Use start ')
        parser.add_argument('--verbose',action='store_true', dest='verbose', default=False, help='Set verbosity level for books duplicates checker.')
        
    def handle(self, *args, **options): 
        self.pidfile = os.path.join(main_settings.BASE_DIR, config.SOPDS_SCANNER_PID)
        action = options['command']            
        self.logger = logging.getLogger('')
        self.logger.setLevel(logging.DEBUG)
        formatter=logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')

        if settings.LOGLEVEL!=logging.NOTSET:
            # Создаем обработчик для записи логов в файл
            fh = logging.FileHandler(config.SOPDS_SCANNER_LOG)
            fh.setLevel(settings.LOGLEVEL)
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

        if options['verbose']:
            # Создадим обработчик для вывода логов на экран с максимальным уровнем вывода
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)
            

        if action=='start':
            self.stdout.write('Startup once book duplicates scan.')
            if self.scan_is_active:
                self.stdout.write('Scan process already active. Skip current job.')
                return
        
            self.scan_is_active = True
            found_doubles = []
            for book in Book.objects.all():
                self.logger.info(f"Check duplicates for book_id {book.id}")
                if book.id not in found_doubles:
                    for book_doubles in Book.objects.filter(title=book.title, authors__in=book.authors.all()).exclude(id=book.id).distinct().order_by('-docdate'):
                        self.logger.info (f"Found duplicate id {book_doubles.id} for book {book.id}")
                        found_doubles.append(book_doubles.id)
            
            self.scan_is_active = False
            self.stdout.write('Complete book duplicates scan.')        

