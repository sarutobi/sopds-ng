"""Фикстуры для моделей opds_catalog."""

import datetime

from django.conf import settings as main_settings
from django.contrib.auth.models import User
from django.utils import timezone

import pytest

from opds_catalog.models import (
    Author,
    Book,
    Catalog,
    Counter,
    Genre,
    Series,
    bauthor,
    bgenre,
    bseries,
    bookshelf,
)


@pytest.fixture
def test_datetime():
    """Возвращает фиксированную дату с учётом настройки USE_TZ."""
    dt = datetime.datetime(2016, 1, 1, 0, 0)
    if main_settings.USE_TZ:
        dt = dt.replace(tzinfo=timezone.get_current_timezone())
    return dt


@pytest.fixture
def catalog():
    """Создаёт корневой каталог."""
    return Catalog.objects.create(
        parent=None,
        cat_name=".",
        path=".",
        cat_type=0,
    )


@pytest.fixture
def book(catalog, test_datetime):
    """Создаёт книгу с минимальными полями."""
    return Book.objects.create(
        filename="testbook.fb2",
        path=".",
        filesize=500,
        format="fb2",
        cat_type=0,
        registerdate=test_datetime,
        docdate="01.01.2016",
        lang="ru",
        title="Книга",
        search_title="КНИГА",
        annotation="Аннотация",
        avail=2,
        catalog=catalog,
    )


@pytest.fixture
def author():
    """Создаёт автора."""
    return Author.objects.create(
        full_name="Шелепнев Дмитрий",
        search_full_name="ШЕЛЕПНЕВ ДМИТРИЙ",
    )


@pytest.fixture
def genre():
    """Создаёт жанр."""
    return Genre.objects.create(
        genre="fantastic0",
        section="fantastic1",
        subsection="fantastic2",
    )


@pytest.fixture
def series():
    """Создаёт серию."""
    return Series.objects.create(
        ser="mywork",
        search_ser="MYWORK",
    )


@pytest.fixture
def user():
    """Создаёт тестового пользователя."""
    return User.objects.create_user(
        "testuser",
        "testuser@sopds.ru",
        "testpassword",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def book_with_relations(book, author, genre, series):
    """Создаёт книгу, связанную с автором, жанром и серией."""
    bauthor.objects.create(book=book, author=author)
    bgenre.objects.create(book=book, genre=genre)
    bseries.objects.create(book=book, ser=series, ser_no=1)
    return book


@pytest.fixture
def bookshelf_entry(book_with_relations, user, test_datetime):
    """Создаёт запись на книжной полке."""
    return bookshelf.objects.create(
        user=user,
        book=book_with_relations,
        readtime=test_datetime,
    )


@pytest.fixture
def update_counters():
    """Обновляет все известные счётчики (вызов update_known_counters)."""
    Counter.objects.update_known_counters()
    return
