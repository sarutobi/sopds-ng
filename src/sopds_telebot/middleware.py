from django.contrib.auth.models import User
from django.db import connection, connections
from django.utils import translation

from opds_catalog.config import catalog_config


def cmdtrans(func):
    """Декоратор для активации языка каталога на время выполнения функции."""

    def wrapper(self, bot, update):
        translation.activate(catalog_config.CURRENT_LANGUAGE)
        result = func(self, bot, update)
        translation.deactivate()
        return result

    return wrapper


def CheckAuthDecorator(func):
    """Декоратор для проверки прав доступа Telegram-пользователя."""

    def wrapper(self, bot, update):
        if not catalog_config.BOT_AUTH_ENABLED:
            return func(self, bot, update)

        if connection.connection and not connection.is_usable():
            del connections._connections.default

        query = update.message or update.callback_query.message
        username = (
            update.message.from_user.username
            if update.message
            else update.callback_query.from_user.username
        )
        users = User.objects.filter(username__iexact=username)

        if users and users[0].is_active:
            return func(self, bot, update)

        bot.sendMessage(
            chat_id=query.chat_id,
            text=f"Hello {username}!\nUnfortunately you do not have access to information. Please contact the bot administrator.",
        )
        self.logger.info(f"Denied access for user: {username}")

        return

    return wrapper
