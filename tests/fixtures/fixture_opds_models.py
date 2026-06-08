"""Фикстуры моделей opds_catalog."""

import pytest

from opds_catalog.models import Author, Book, Catalog, Genre, bauthor


@pytest.fixture
def catalog():
    """Фикстура для создания тестового каталога.

    Создаёт запись ``Catalog`` с именем ``"Test Catalog"``, путём ``"/test/path"``.

    :scope: session
    :returns: Catalog
    :rtype: opds_catalog.models.Catalog
    """
    return Catalog.objects.create(
        cat_name="Test Catalog", path="/test/path", cat_type=0, cat_size=0
    )


@pytest.fixture
def author():
    """Фикстура для создания тестового автора.

    Создаёт одного автора — ``Author`` с именем ``"Иван Иванов"`` (кириллица, lang_code=1).

    :scope: session
    :returns: Author
    :rtype: opds_catalog.models.Author
    """
    return Author.objects.create(
        full_name="Иван Иванов", search_full_name="ИВАН ИВАНОВ", lang_code=1
    )


@pytest.fixture
def author_cyrillic():
    """Автор с кириллическим именем.

    Создаёт автора с именем ``"Александр Пушкин"`` (lang_code=1).

    :scope: session
    :returns: Author
    :rtype: opds_catalog.models.Author
    """
    return Author.objects.create(
        full_name="Александр Пушкин", search_full_name="АЛЕКСАНДР ПУШКИН", lang_code=1
    )


@pytest.fixture
def author_latin():
    """Автор с латинским именем.

    Создаёт автора с именем ``"John Smith"`` (lang_code=2).

    :scope: session
    :returns: Author
    :rtype: opds_catalog.models.Author
    """
    return Author.objects.create(
        full_name="John Smith", search_full_name="JOHN SMITH", lang_code=2
    )


@pytest.fixture
def author_with_books(catalog, author):
    """Автор с несколькими книгами.

    Автор, которому принадлежат две книги (``book1`` и ``book2``). Книги привязаны через
    ``bauthor``. Полезно для тестов, где требуется автор с реальными книгами.

    :scope: session
    :returns: Author
    :rtype: opds_catalog.models.Author
    """
    book1 = Book.objects.create(
        filename="book1.fb2",
        path="/books",
        filesize=1024,
        format="fb2",
        catalog=catalog,
        cat_type=0,
        docdate="2020",
        lang="ru",
        title="Книга 1",
        search_title="КНИГА 1",
        annotation="Аннотация 1",
        lang_code=1,
        avail=1,
    )
    book2 = Book.objects.create(
        filename="book2.fb2",
        path="/books",
        filesize=2048,
        format="fb2",
        catalog=catalog,
        cat_type=0,
        docdate="2021",
        lang="ru",
        title="Книга 2",
        search_title="КНИГА 2",
        annotation="Аннотация 2",
        lang_code=1,
        avail=1,
    )
    bauthor.objects.create(book=book1, author=author)
    bauthor.objects.create(book=book2, author=author)
    return author


@pytest.fixture
def multiple_authors():
    """Несколько авторов для тестов поиска.

    Список из пяти авторов с разными именами и кодами языка. Используется для тестов поиска
    и сортировки.

    :scope: session
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

    :scope: function
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

    :scope: function
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


@pytest.fixture
def genre() -> Genre:
    """Жанр книги.

    Создаёт запись ``Genre`` с секцией ``"Section A"`` и подсекцией ``"Subsection A1"``.

    :scope: session
    :returns: Genre
    :rtype: opds_catalog.models.Genre
    """
    return Genre.objects.create(section="Section A", subsection="Subsection A1")


@pytest.fixture
def book(genre) -> Book:
    """Книга.

    Создаёт одну запись ``Book`` с названием ``"Test title"`` и привязанным жанром.

    :scope: session
    :returns: Book
    :rtype: opds_catalog.models.Book
    """
    return Book.objects.create(title="Test title", genre=genre)
