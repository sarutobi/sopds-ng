import pytest
from django.test import RequestFactory

from opds_catalog.models import Book, Catalog, Counter
from src.sopds_web_backend.processors import sopds_processor


@pytest.mark.django_db
def test_sopds_processor_outdated_counter_no_index_error():
    # Проверка, что если значение 'allbooks' в Counter больше реального количества книг,
    # это больше НЕ приводит к IndexError.
    rf = RequestFactory()
    request = rf.get("/")
    request.user = type("User", (), {"is_authenticated": False})()

    # Создаем каталог
    catalog = Catalog.objects.create(cat_name="Test Catalog", path="/test/", cat_type=0)

    # Создаем одну книгу
    Book.objects.create(
        title="Book 1",
        search_title="Book 1",
        filename="book1.fb2",
        path="/books/book1.fb2",
        catalog=catalog,
        format="fb2",
        lang="ru",
        annotation="",
    )

    # Создаем запись в Counter, которая говорит, что книг 10 (устаревшее значение)
    Counter.objects.create(name="allbooks", value=10)

    # Теперь, независимо от того, что в Counter, IndexError не должен возникнуть,
    # так как Book.objects.count() вернет 1.
    for _ in range(100):
        try:
            args = sopds_processor(request)
            assert "random_book" in args
        except IndexError:
            pytest.fail("IndexError was raised despite fix")
