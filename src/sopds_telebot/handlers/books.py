import logging
import re

from django.utils.translation import gettext as _

from opds_catalog import dl
from opds_catalog.models import Book
from opds_catalog.services.book_services import filter_books
from sopds_telebot.services.pager import BookPager

logger = logging.getLogger(__name__)


def handle_get_books(bot, update, command_ctx):
    """Обработчик команды /getbooks."""
    query = update.message.text.replace("/getbooks ", "").strip()
    if not query:
        response = _("Please enter a search query. For example: /getbooks Tolkien")
        bot.send_message(
            chat_id=update.message.chat_id, text=response, parse_mode="HTML"
        )
        return

    if len(query) < 3:
        response = _("Too short for search, please try again.")
        bot.send_message(chat_id=update.message.chat_id, text=response)
        return

    books = filter_books(query)
    books_count = books.count()

    if books_count == 0:
        response = _("No results were found for your query, please try again.")
        bot.send_message(chat_id=update.message.chat_id, text=response)
        return

    response = (
        _(
            "Found %s books.\nI create list, after a few seconds, select the file to download:"
        )
        % books_count
    )
    bot.send_message(chat_id=update.message.chat_id, text=response)

    # Вызов пагинации
    command_ctx.get_books_page(bot, update, query, 1)


def handle_get_books_page(bot, update, books, page_num, command_ctx):
    """Обработчик пагинации списка книг."""
    query = "запрос"
    if update.callback_query:
        data = update.callback_query.data
        if "####" in data:
            query = data.split("####")[0]

    from django.conf import settings

    max_items = getattr(settings, "SOPDS_TELEBOT_MAXITEMS", 10)
    hide_doubles = getattr(settings, "SOPDS_DOUBLES_HIDE", True)

    pager = BookPager(
        books, page_num, query, max_items=max_items, hide_doubles=hide_doubles
    )
    response_data = pager.get_page_items()

    message_text = command_ctx._build_pager_message(response_data)
    buttons = command_ctx._build_pager_buttons(response_data, query)

    if update.callback_query:
        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            message_id=update.callback_query.message.message_id,
            text=message_text,
            parse_mode="HTML",
            reply_markup=buttons,
        )
    else:
        bot.send_message(
            chat_id=update.message.chat_id,
            text=message_text,
            parse_mode="HTML",
            reply_markup=buttons,
        )


def handle_download_books(bot, update, command_ctx):
    """Обработчик команды /download {id}."""
    book_id_set = re.findall(r"\d+$", update.message.text)
    if len(book_id_set) == 1:
        try:
            book_id = int(book_id_set[0])
            book = Book.objects.get(id=book_id)
        except Exception:
            book = None
    else:
        book = None

    if book == None:
        response = _(
            "The book on the link you specified is not found, try to repeat the book search first."
        )
        bot.send_message(
            chat_id=update.message.chat_id, text=response, parse_mode="HTML"
        )
        return

    authors = ", ".join([a["full_name"] for a in book.authors.values()])
    response = (
        "<b>%(title)s</b>\n%(author)s\n<b>" + _("Annotation:") + "</b>%(annotation)s\n"
    ) % {"title": book.title, "author": authors, "annotation": book.annotation}

    bot.send_message(
        chat_id=update.message.chat_id,
        text=response,
        parse_mode="HTML",
        reply_markup=command_ctx._build_download_buttons(book),
    )


def handle_get_book_file(bot, update, command_ctx):
    """Обработчик получения файла книги."""
    callback_query = update.callback_query
    query = callback_query.data
    book_id_set = re.findall(r"\d+$", query)

    if len(book_id_set) == 1:
        try:
            book_id = int(book_id_set[0])
            book = Book.objects.get(id=book_id)
        except Exception:
            book = None
    else:
        book = None

    if book == None:
        response = _(
            "The book on the link you specified is not found, try to repeat the book search first."
        )
        bot.send_message(
            chat_id=callback_query.message.chat_id, text=response, parse_mode="HTML"
        )
        return

    from opds_catalog import utils as catalog_utils

    filename = dl.getFileName(book)
    document = None

    format_map = {
        r"/getfileorig": (dl.getFileData, ""),
        r"/getfilezip": (catalog_utils.getFileDataZip, ".zip"),
        r"/getfileepub": (catalog_utils.getFileDataEpub, ".epub"),
        r"/getfilemobi": (catalog_utils.getFileDataMobi, ".mobi"),
    }

    for pattern, (fetch_func, ext) in format_map.items():
        if re.match(pattern, query):
            document = fetch_func(book)
            filename += ext
            break

    if document:
        bot.send_document(
            chat_id=callback_query.message.chat_id,
            document=document,
            filename=filename,
        )
        document.close()
    else:
        response = _(
            "There was a technical error, please contact the Bot administrator."
        )
        bot.send_message(
            chat_id=callback_query.message.chat_id, text=response, parse_mode="HTML"
        )
