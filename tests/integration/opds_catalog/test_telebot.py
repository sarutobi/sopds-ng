"""Интеграционные тесты для приложения sopds_telebot.

Проверяют основные пользовательские сценарии:
- Поиск книг.
- Пагинация результатов.
- Получение ссылок на скачивание.
- Выдача файлов книг.
- Авторизация и управление жизненным циклом.
"""

import logging
import os

import pytest
from constance.test import override_config
from django.contrib.auth.models import User

from opds_catalog import dl
from opds_catalog.management.commands.sopds_telebot import Command
from opds_catalog.models import Author, Book, Catalog, bauthor

pytestmark = pytest.mark.django_db

# ---------------------------------------------------------------------------
# Fake Telegram API
# ---------------------------------------------------------------------------


class FakeUser:
    def __init__(self, username: str):
        self.username = username


class FakeMessage:
    def __init__(self, text: str = "", chat_id: int = 1, username: str = "tguser"):
        self.text = text
        self.chat_id = chat_id
        self.from_user = FakeUser(username)


class FakeCallbackQuery:
    def __init__(
        self,
        data: str,
        chat_id: int = 1,
        message_id: int = 100,
        username: str = "tguser",
    ):
        self.data = data
        self.message = FakeMessage(chat_id=chat_id)
        self.message.message_id = message_id
        self.from_user = FakeUser(username)


class FakeUpdate:
    def __init__(self, message=None, callback_query=None):
        self.message = message
        self.callback_query = callback_query


class FakeBot:
    def __init__(self):
        self.calls = []

    def _record(self, name, **kwargs):
        self.calls.append((name, kwargs))

    def send_message(self, **kwargs):
        self._record("send_message", **kwargs)

    def sendMessage(self, **kwargs):
        self.send_message(**kwargs)

    def edit_message_text(self, **kwargs):
        self._record("edit_message_text", **kwargs)

    def editMessageText(self, **kwargs):
        self.edit_message_text(**kwargs)

    def send_document(self, **kwargs):
        self._record("send_document", **kwargs)

    def calls_of(self, name: str):
        return [kwargs for method, kwargs in self.calls if method == name]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def catalog():
    return Catalog.objects.create(cat_name=".", path=".", cat_type=0)


@pytest.fixture
def command():
    cmd = Command()
    cmd.logger = logging.getLogger("test_telebot")
    cmd.logger.setLevel(logging.CRITICAL)
    return cmd


@pytest.fixture
def bot():
    return FakeBot()


def make_book(title, search_title, docdate, filename, author_name=None, catalog=None):
    book = Book.objects.create(
        filename=filename,
        path=".",
        filesize=2500,
        format="fb2",
        cat_type=0,
        docdate=docdate,
        lang="ru",
        title=title,
        search_title=search_title,
        annotation=f"Annotation {title}",
        avail=2,
        catalog=catalog,
    )
    if author_name:
        author = Author.objects.create(
            full_name=author_name, search_full_name=author_name.upper()
        )
        bauthor.objects.create(book=book, author=author)
    return book


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBotSearch:
    def test_search_found_books(self, command, bot, catalog):
        """Поиск по существующим книгам возвращает список."""
        make_book("Tolkien Book", "TOLKIEN", "2025", "tolk.fb2", catalog=catalog)
        update = FakeUpdate(message=FakeMessage(text="/getbooks Tolkien"))

        with override_config(SOPDS_TELEBOT_AUTH=False):
            command.getBooks(bot, update)

        # Ожидаем: 1. Подтверждение поиска, 2. Список книг (через send_message)
        sends = bot.calls_of("send_message")
        assert len(sends) >= 2
        assert "Tolkien Book" in sends[1]["text"]

    def test_search_no_results(self, command, bot, catalog):
        """Поиск без результатов возвращает сообщение об ошибке."""
        update = FakeUpdate(message=FakeMessage(text="/getbooks UnknownAuthor"))

        with override_config(SOPDS_TELEBOT_AUTH=False):
            command.getBooks(bot, update)

        sends = bot.calls_of("send_message")
        assert any("No results" in s["text"] for s in sends)

    def test_search_too_short(self, command, bot, catalog):
        """Слишком короткий запрос возвращает подсказку."""
        update = FakeUpdate(message=FakeMessage(text="/getbooks ab"))

        with override_config(SOPDS_TELEBOT_AUTH=False):
            command.getBooks(bot, update)

        sends = bot.calls_of("send_message")
        assert any("Too short" in s["text"] for s in sends)


class TestBotPagination:
    def test_pagination_navigation(self, command, bot, catalog):
        """Нажатие на кнопку пагинации обновляет сообщение."""
        for i in range(5):
            # Важно: search_title должен быть одинаковым, чтобы они попали в один поиск
            make_book(f"Book {i}", "BOOK", "2025", f"b{i}.fb2", catalog=catalog)

        # Эмулируем переход на 2-ю страницу для запроса "BOOK"
        update = FakeUpdate(callback_query=FakeCallbackQuery(data="BOOK####2"))

        # Используем прямое изменение settings, так как override_config может не срабатывать в BookPager
        from django.conf import settings

        old_max = getattr(settings, "SOPDS_TELEBOT_MAXITEMS", 10)
        settings.SOPDS_TELEBOT_MAXITEMS = 2
        try:
            with override_config(SOPDS_TELEBOT_AUTH=False, SOPDS_DOUBLES_HIDE=False):
                command.botCallback(bot, update)
        finally:
            settings.SOPDS_TELEBOT_MAXITEMS = old_max

        edits = bot.calls_of("edit_message_text")
        assert len(edits) == 1
        assert "Book" in edits[0]["text"]


class TestBotDownload:
    def test_download_command_shows_formats(self, command, bot, catalog):
        """Команда /download возвращает кнопки форматов."""
        book = make_book("Download Me", "DL", "2025", "dl.fb2", catalog=catalog)
        update = FakeUpdate(message=FakeMessage(text=f"/download{book.id}"))

        with override_config(SOPDS_TELEBOT_AUTH=False):
            command.downloadBooks(bot, update)

        sends = bot.calls_of("send_message")
        assert len(sends) == 1
        markup = sends[0]["reply_markup"]
        assert markup is not None
        # Проверяем наличие кнопки с форматом (FB2)
        assert any("FB2" in b.text for b in markup.inline_keyboard[0])

    def test_get_file_sends_document(self, command, bot, catalog, monkeypatch):
        """Выбор формата отправляет файл."""
        book = make_book("File Book", "FILE", "2025", "file.fb2", catalog=catalog)

        # Патчим dl.getFileData, чтобы он возвращал заглушку вместо попытки читать диск
        from opds_catalog import dl

        class MockDoc:
            def close(self):
                pass

        monkeypatch.setattr(dl, "getFileData", lambda b: MockDoc())

        update = FakeUpdate(
            callback_query=FakeCallbackQuery(data=f"/getfileorig{book.id}")
        )

        with override_config(SOPDS_TELEBOT_AUTH=False):
            command.botCallback(bot, update)

        docs = bot.calls_of("send_document")
        assert len(docs) == 1
        assert docs[0]["filename"].endswith(".fb2")


class TestBotAuth:
    def test_auth_denies_unknown_user(self, command, bot):
        """Неавторизованный пользователь получает отказ."""
        update = FakeUpdate(
            message=FakeMessage(text="/getbooks Tolkien", username="stranger")
        )

        with override_config(SOPDS_TELEBOT_AUTH=True):
            command.getBooks(bot, update)

        sends = bot.calls_of("send_message")
        assert any("do not have access" in s["text"] for s in sends)


class TestLifecycle:
    def test_stop_process(self, command, monkeypatch):
        """Команда stop вызывает kill_process."""
        import os
        import signal

        def mock_kill(pid, sig):
            return True

        monkeypatch.setattr(os, "kill", mock_kill)

        # Просто проверяем, что метод не падает
        command.stop("12345")
