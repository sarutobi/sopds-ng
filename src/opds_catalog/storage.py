"""Работа с хранилищем данных."""

from django.db.models import QuerySet
from opds_catalog.models import Book, bookshelf, Catalog, Counter
from django.contrib.auth.models import User


def get_book_by_id(id: int) -> Book:
    """Поиск книги по идентификатору."""
    return Book.objects.get(id=id)


def add_book_to_bookshelf(user: User, book: Book) -> None:
    """Добавляет книгу на книжную полку пользователя, если такой книги еще нет."""
    bookshelf.objects.get_or_create(user=user, book=book)


def get_root_catalog() -> Catalog | None:
    """Возвращает корневой каталог."""
    return Catalog.objects.get(parent__id=None)


def get_catalog_by_id(id: int) -> Catalog | None:
    """Возвращает каталог по идентификатору.

    :param id: Идентификатор каталога
    :type id: int

    :returns: Найденный каталог или None если каталога с таким идентификатором не существует
    :rtype: Catalog | None
    """
    try:
        return Catalog.objects.get(id=id)
    except Catalog.DoesNotExist:
        return None


def get_child_catalog_query(root: Catalog | None) -> QuerySet[Catalog, Catalog]:
    """Запрос подкаталогов текущего каталога.

    :param root: каталог, для которого требуется найти подкаталоги
    :type root: Catalog|None

    :returns: Запрос, позволяющий получить подкаталоги
    :rtype: QuerySet[Catalog, Catalog]
    """
    return Catalog.objects.filter(parent=root)


def get_books_in_catalog_query(catalog: Catalog) -> QuerySet[Book, Book]:
    """Запрос книг в каталоге.

    :param catalog: каталог, в котором требуется найти книги
    :type catalog: Catalog

    :returns: Запрос, позволяющий получить книги
    :rtype: Queryset[Book, Book]
    """
    return Book.objects.filter(catalog=catalog)


def get_counter(counter_name: str) -> int:
    """Возвращает значение счетчика.

    :param counter_name: Наименование счетчика
    :type counter_name: str

    :returns: значение запрошенного счетчика
    :rtype: int
    """
    return Counter.objects.get_counter(counter_name)


def get_bookshelf_books_count(user: User) -> int:
    """Подсчет числа книг на книжной полке пользователя.

    :param user: Пользователь, для котрого требуется подсчитать число книг.
    :type user: User

    :returns: Число книг на книжной полке.
    :rtype: int
    """
    return bookshelf.objects.filter(user=user).count()
