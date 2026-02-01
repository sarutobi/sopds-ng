# Фикстуры для Django

import pytest
from django.core.management import call_command
from tests.opds_catalog.helpers import create_book
from opds_catalog import opdsdb
from opds_catalog.models import Book, Catalog


@pytest.fixture
def django_user(django_user_model):
    """Обычный пользователь django"""
    user = django_user_model.objects.create_user(username="test", password="secret")
    yield user


@pytest.fixture
def auth_client(client, django_user):
    """Авторизовнный пользователь django"""
    client.force_login(django_user)
    yield client


@pytest.fixture
def load_db_data(django_db_setup, django_db_blocker):
    """Чтение слепка данных из файла json"""
    with django_db_blocker.unblock():
        call_command("loaddata", "testdb.json")


@pytest.fixture
def create_regular_book(simple_fb2):
    # book = create_book(filename=simple_fb2, cat_type=opdsdb.CAT_NORMAL, path=".")
    catalog = Catalog(cat_name="test_catalog", path=".")
    catalog.save()
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
    catalog.delete()


@pytest.fixture
def unexisted_book():
    b = Book(id=4, search_title="UNEXISTED", catalog_id=1)
    b.save()
    yield
    b.delete()
