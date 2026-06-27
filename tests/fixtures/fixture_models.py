"""Фикстуры для моделей opds_catalog."""

import datetime

import pytest
from django.conf import settings as main_settings
from django.contrib.auth.models import User
from django.utils import timezone

from opds_catalog.models import (
    Author,
    Book,
    Catalog,
    Counter,
    Genre,
    Series,
    bauthor,
    bgenre,
    bookshelf,
    bseries,
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


# ---------------------------------------------------------------------------
# Фикстуры для сервисов авторов (перенесены из fixture_opds_models.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def multiple_authors():
    """Несколько авторов для тестов поиска.

    Список из пяти авторов с разными именами и кодами языка. Используется для тестов поиска
    и сортировки.

    :returns: list[Author]
    :rtype: list
    """
    authors_data = [
        ("АБРАМОВ", "АБРАМОВ", 1),
        ("АБРАМОВИЧ", "АБРАМОВИЧ", 1),
        ("БРАМОВ", "БРАМОВ", 2),
        ("СИДОРОВ", "СИДОРОВ", 1),
        ("SIDOROV", "SIDOROV", 2),
    ]
    authors = []
    for full_name, search_name, lang_code in authors_data:
        author = Author.objects.create(
            full_name=full_name, search_full_name=search_name, lang_code=lang_code
        )
        authors.append(author)
    return authors


@pytest.fixture(
    params=[
        # (full_name, search_full_name, lang_code)
        ("Иван Иванов", "ИВАН ИВАНОВ", 1),  # Кириллица
        ("John Smith", "JOHN SMITH", 2),  # Латиница
        ("123 Author", "123 AUTHOR", 3),  # Цифры
        ("Special !@#", "SPECIAL !@#", 9),  # Другие символы
        ("", "", 1),  # Пустое имя
    ]
)
def parametrized_author(request):
    """Параметризованная фикстура для создания автора с разными данными.

    Создаёт автора с различными данными (включая пустое имя, цифры, спецсимволы).
    Каждый вызов теста получает один из пяти наборов параметров.

    :param request: объект запроса pytest
    :type request: FixtureRequest
    :returns: Author
    :rtype: opds_catalog.models.Author
    """
    full_name, search_full_name, lang_code = request.param
    return Author.objects.create(
        full_name=full_name, search_full_name=search_full_name, lang_code=lang_code
    )


@pytest.fixture(
    params=[
        # (full_name, search_full_name, lang_code, book_count)
        ("Александр Пушкин", "АЛЕКСАНДР ПУШКИН", 1, 3),
        ("Leo Tolstoy", "LEO TOLSTOY", 2, 5),
        ("Author 123", "AUTHOR 123", 3, 1),
        ("Тест Автор", "ТЕСТ АВТОР", 1, 0),  # Автор без книг
    ]
)
def parametrized_author_with_books(request, catalog):
    """Параметризованная фикстура для создания автора с указанным количеством книг.

    Создаёт автора и указанное количество книг (от 0 до 5).
    Типовые наборы: Пушкин (3 кн.), Толстой (5 кн.), Author 123 (1 кн.), Тест Автор (0 кн.).

    :param request: объект запроса pytest
    :type request: FixtureRequest
    :param catalog: Catalog
    :type catalog: opds_catalog.models.Catalog
    :returns: Author
    :rtype: opds_catalog.models.Author
    """
    full_name, search_full_name, lang_code, book_count = request.param

    author = Author.objects.create(
        full_name=full_name, search_full_name=search_full_name, lang_code=lang_code
    )

    # Создаем указанное количество книг и связываем их с автором
    for i in range(book_count):
        book = Book.objects.create(
            filename=f"book_{full_name}_{i}.fb2",
            path="/books",
            filesize=1024 * (i + 1),
            format="fb2",
            catalog=catalog,
            cat_type=0,
            docdate="2020",
            lang="ru",
            title=f"Книга {i} автора {full_name}",
            search_title=f"КНИГА {i} АВТОРА {search_full_name}",
            annotation=f"Аннотация {i}",
            lang_code=lang_code,
            avail=1,
        )
        bauthor.objects.create(book=book, author=author)

    return author
