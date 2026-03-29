"""Сервисы для работы с книжной полкой пользователя."""

from opds_catalog.models import Book, bookshelf
from django.contrib.auth.models import User


def get_bookshelf_books_count(user: User) -> int:
    """Подсчет числа книг на книжной полке пользователя.

    :param user: Пользователь, для котрого требуется подсчитать число книг.
    :type user: User

    :returns: Число книг на книжной полке.
    :rtype: int
    """
    return bookshelf.objects.filter(user=user).count()


def add_book_to_bookshelf(user: User, book: Book) -> None:
    """Добавляет книгу на книжную полку пользователя, если такой книги еще нет."""
    bookshelf.objects.get_or_create(user=user, book=book)
