# Фикстуры для Django

from django.core.management import call_command
from django.test import RequestFactory
import pytest

from opds_catalog import opdsdb
from opds_catalog.models import Book


@pytest.fixture
def request_factory() -> RequestFactory:
    """RequestFactory.

    Экземпляр ``RequestFactory`` из Django. Удобен для создания тестовых запросов без
    полного WSGI‑стэка.

    :scope: function
    :returns: RequestFactory
    :rtype: django.test.RequestFactory
    """
    return RequestFactory()


@pytest.fixture
def django_user(django_user_model):
    """Обычный пользователь django.

    Создаёт обычного пользователя Django (логин ``"test"``, пароль ``"secret"``).

    :scope: function
    :returns: User
    :rtype: django.contrib.auth.models.User
    """
    user = django_user_model.objects.create_user(username="test", password="secret")
    yield user


@pytest.fixture
def auth_client(client, django_user):
    """Авторизованный пользователь django.

    Клиент Django с принудительной авторизацией от имени ``django_user``.
    Используется в тестах, требующих аутентифицированных запросов.

    :scope: function
    :param client: Django test client
    :type client: django.test.Client
    :param django_user: тестовый пользователь
    :type django_user: django.contrib.auth.models.User
    :returns: Django test client (авторизованный)
    :rtype: django.test.Client
    """
    client.force_login(django_user)
    yield client


@pytest.fixture
def load_db_data(django_db_setup, django_db_blocker):
    """Чтение слепка данных из файла json.

    Выполняет ``loaddata testdb.json`` для загрузки слепка тестовых данных из JSON.
    Гарантирует доступ к записям, подготовленным вне модельных фикстур.

    :scope: function
    :yields: None
    """
    with django_db_blocker.unblock():
        call_command("loaddata", "testdb.json")


@pytest.fixture
def create_regular_book(simple_fb2, catalog):
    """Создаёт книгу (экземпляр ``Book``).

    Создаёт книгу с именем файла ``simple_fb2``, категорией ``opdsdb.CAT_NORMAL`` и путём ``"."``.
    Использует общую фикстуру ``catalog`` вместо создания собственного каталога.

    :scope: function
    :param simple_fb2: имя файла
    :type simple_fb2: str
    :param catalog: Catalog из фикстуры
    :type catalog: opds_catalog.models.Catalog
    :returns: Book
    :rtype: opds_catalog.models.Book
    """
    book = Book(
        filename=simple_fb2,
        cat_type=opdsdb.CAT_NORMAL,
        path=".",
        format="fb2",
        search_title="1",
        catalog=catalog,
    )
    book.save()
    yield book
    book.delete()


@pytest.fixture
def unexisted_book():
    """Создаёт книгу, удаляемую после теста.

    Создаёт книгу с ``id=4``, ``search_title="UNEXISTED"`` и ``catalog_id=1``.
    Удаляется после теста. Используется для проверки, что поиск по несуществующим
    ключам возвращает ожидаемый результат.

    :scope: function
    :returns: Book
    :rtype: opds_catalog.models.Book
    """
    b = Book(id=4, search_title="UNEXISTED", catalog_id=1)
    b.save()
    yield
    b.delete()


@pytest.fixture
def book_factory():
    """Создаёт Book-объект без сохранения в БД.

    Возвращает функцию ``factory(title='', format='', filename='', cat_type=0, path='')``,
    которая создаёт и возвращает экземпляр ``Book`` без сохранения.

    :scope: function
    :returns: callable
    """

    def _factory(title="", format="", filename="", cat_type=0, path="") -> Book:
        return Book(
            title=title,
            format=format,
            filename=filename,
            cat_type=cat_type,
            path=path,
        )

    return _factory
