import logging
import os
import re
import signal
import sys

from django.conf import settings as main_settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import connection, connections
from django.db.models import Q
from django.utils import translation
from django.utils.html import strip_tags
from django.utils.translation import gettext as _
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import InvalidToken
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    Updater,
    filters,
)

from opds_catalog import dl, settings
from opds_catalog.config import catalog_config
from opds_catalog.models import Book
from sopds_telebot.handlers.books import (
    handle_download_books,
    handle_get_book_file,
    handle_get_books,
    handle_get_books_page,
)
from sopds_telebot.middleware import CheckAuthDecorator, cmdtrans
from sopds_telebot.utils import daemonize, kill_process, writepid

query_delimiter = "####"


class Command(BaseCommand):
    help = "SimpleOPDS Telegram Bot engine."
    can_import_settings = True
    leave_locale_alone = True

    def add_arguments(self, parser):
        parser.add_argument("command", help="Use [ start | stop | restart ]")
        parser.add_argument(
            "--verbose",
            action="store_true",
            dest="verbose",
            default=False,
            help="Set verbosity level for SimpleOPDS telebot.",
        )
        parser.add_argument(
            "--daemon",
            action="store_true",
            dest="daemonize",
            default=False,
            help="Daemonize server",
        )

    def handle(self, *args, **options):
        self.pidfile = os.path.join(main_settings.BASE_DIR, catalog_config.BOT_PID_FILE)
        action = options["command"]
        self.logger = logging.getLogger("")
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")

        if settings.LOGLEVEL != logging.NOTSET:
            # Создаем обработчик для записи логов в файл
            fh = logging.FileHandler(catalog_config.BOT_LOG_FILE)
            fh.setLevel(settings.LOGLEVEL)
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

        if options["verbose"]:
            # Создадим обработчик для вывода логов на экран с максимальным уровнем вывода
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

        if options["daemonize"] and (action in ["start"]):
            if sys.platform == "win32":
                self.stdout.write("On Windows platform Daemonize not working.")
            else:
                daemonize()

        if action == "start":
            self.start()
        elif action == "stop":
            pid = open(self.pidfile, "r").read()
            self.stop(pid)
        elif action == "restart":
            pid = open(self.pidfile, "r").read()
            self.restart(pid)

    @cmdtrans
    @CheckAuthDecorator
    def startCommand(self, bot, update):
        bot.sendMessage(
            chat_id=update.message.chat_id,
            text=_(
                "%(subtitle)s\nHello %(username)s! To search for a book, enter part of her title or author:"
            )
            % {
                "subtitle": settings.SUBTITLE,
                "username": update.message.from_user.username,
            },
        )
        self.logger.info("Start talking with user: %s" % update.message.from_user)

    def BookFilter(self, query):
        """Делегирование поиску в сервисном слое."""
        from opds_catalog.services.book_services import filter_books

        return filter_books(query)

    def BookPager(self, books, page_num, query):
        """Делегирование пагинации в сервисный слой."""
        from sopds_telebot.services.pager import BookPager

        return BookPager(books, page_num, query)

    @cmdtrans
    @CheckAuthDecorator
    def getBooks(self, bot, update):
        handle_get_books(bot, update, self)

    def get_books_page(self, bot, update, query, page_num):
        """Метод-посредник для вызова хендлера пагинации."""
        from opds_catalog.services.book_services import filter_books

        books = filter_books(query)
        handle_get_books_page(bot, update, books, page_num, self)

    @cmdtrans
    @CheckAuthDecorator
    def downloadBooks(self, bot, update):
        handle_download_books(bot, update, self)

    @cmdtrans
    @CheckAuthDecorator
    def getBookFile(self, bot, update):
        handle_get_book_file(bot, update, self)

    @cmdtrans
    @CheckAuthDecorator
    def botCallback(self, bot, update):
        query_obj = update.callback_query

        if not query_obj:
            return

        data = query_obj.data
        if re.match(r"/getfile", data):
            return self.getBookFile(bot, update)
        else:
            # Парсим query и page_num из callback_data (формат: query####page)
            if query_delimiter in data:
                query, page_num = data.split(query_delimiter, 1)
                if page_num == "current":
                    return
                try:
                    page_num = int(page_num)
                except ValueError:
                    page_num = 1
                return self.get_books_page(bot, update, query, page_num)

            return self.get_books_page(bot, update, "", 1)

    def start(self):
        writepid(self.pidfile)
        quit_command = "CTRL-BREAK" if sys.platform == "win32" else "CONTROL-C"
        self.stdout.write("Quit the sopds_telebot with %s.\n" % quit_command)
        try:
            updater = Updater(token=catalog_config.BOT_TOKEN)  # type: ignore[call-arg]
            start_command_handler = CommandHandler("start", self.startCommand)
            getBook_handler = MessageHandler(filters.TEXT, self.getBooks)
            download_handler = MessageHandler(
                filters.Regex(r"^/download\d+$"), self.downloadBooks
            )

            updater.dispatcher.add_handler(start_command_handler)
            updater.dispatcher.add_handler(getBook_handler)
            updater.dispatcher.add_handler(download_handler)
            updater.dispatcher.add_handler(CallbackQueryHandler(self.botCallback))

            updater.start_polling(clean=True)  # type: ignore[call-arg, unused-coroutine]
            updater.idle()
        except InvalidToken:
            self.stdout.write(
                "Invalid telegram token.\nSet correct token for telegram API by command:\n"
                ' python3 manage.py sopds_util setconf SOPDS_TELEBOT_API_TOKEN "<token>"'
            )
            self.logger.error("Invalid telegram token.")

        except (KeyboardInterrupt, SystemExit):
            pass

    def _build_pager_message(self, page_data):
        """Формирует HTML-текст страницы книг."""
        items, meta = (
            page_data if isinstance(page_data, tuple) else (page_data[0], page_data[1])
        )

        if not items:
            return _("No books found on this page.")

        lines = []
        for book in items:
            # Теперь items содержит словари, а не объекты Book
            authors_qs = book["authors"]
            authors = ", ".join([a["full_name"] for a in authors_qs])
            doubles = meta["doubles"].get(book["id"], 0)
            doubles_text = (
                f" (doubles: {doubles})"
                if doubles > 0 and not catalog_config.SOPDS_DOUBLES_HIDE
                else ""
            )
            lines.append(
                f"<b>{book['title']}</b>\n{authors}{doubles_text}\n/download{book['id']}\n"
            )

        return "\n".join(lines)

    def _build_pager_buttons(self, page_data, query):
        """Формирует inline-кнопки пагинации."""
        items, meta = (
            page_data if isinstance(page_data, tuple) else (page_data[0], page_data[1])
        )

        keyboard = []
        nav_row = []

        if meta.get("has_prev"):
            nav_row.append(
                InlineKeyboardButton(
                    "⬅️ Prev",
                    callback_data=f"{query}{query_delimiter}{meta['current'] - 1}",
                )
            )
        if meta.get("has_next"):
            nav_row.append(
                InlineKeyboardButton(
                    "Next ➡️",
                    callback_data=f"{query}{query_delimiter}{meta['current'] + 1}",
                )
            )

        if nav_row:
            keyboard.append(nav_row)

        return InlineKeyboardMarkup(keyboard)

    def _build_download_buttons(self, book):
        """Формирует кнопки загрузки для конкретной книги."""
        buttons = [
            InlineKeyboardButton(
                book.format.upper(), callback_data="/getfileorig%s" % book.id
            )
        ]
        if book.format not in settings.NOZIP_FORMATS:
            buttons += [
                InlineKeyboardButton(
                    book.format.upper() + ".ZIP",
                    callback_data="/getfilezip%s" % book.id,
                )
            ]
        if (catalog_config.FB2_TO_EPUB_PATH != "") and (book.format == "fb2"):
            buttons += [
                InlineKeyboardButton("EPUB", callback_data="/getfileepub%s" % book.id)
            ]
        if (catalog_config.FB2_TO_MOBI_PATH != "") and (book.format == "fb2"):
            buttons += [
                InlineKeyboardButton("MOBI", callback_data="/getfilemobi%s" % book.id)
            ]

        return InlineKeyboardMarkup([buttons])

    def stop(self, pid):
        if kill_process(pid):
            self.logger.info(f"Stopped process {pid}")
        else:
            self.stdout.write(f"Error stopping sopds_telebot: {pid}")

    def restart(self, pid):
        self.stop(pid)
        self.start()
