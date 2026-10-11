import pytest
from django.db.models import Prefetch

from opds_catalog.models import Book, Catalog, Series, bseries
from opds_catalog.services.book_services import _build_book_item, book_description


@pytest.mark.django_db
def test_book_series_description_ordering(catalog):
    """Проверка, что номера книг в сериях соответствуют названиям серий в описании."""

    # 1. Создаем книгу
    book = Book.objects.create(
        filename="test.fb2",
        path=".",
        format="fb2",
        title="Test Book",
        search_title="TEST BOOK",
        catalog=catalog,
        lang="ru",
        lang_code=1,
        docdate="2023",
        annotation="Desc",
    )

    # 2. Создаем серии
    s1 = Series.objects.create(ser="Series A", search_ser="SERIES A", lang_code=1)
    s2 = Series.objects.create(ser="Series B", search_ser="SERIES B", lang_code=1)
    s3 = Series.objects.create(ser="Series C", search_ser="SERIES C", lang_code=1)

    # 3. Привязываем книгу к сериям с конкретными номерами
    # Важно: создаем их в определенном порядке
    bseries.objects.create(book=book, ser=s1, ser_no=10)
    bseries.objects.create(book=book, ser=s2, ser_no=20)
    bseries.objects.create(book=book, ser=s3, ser_no=30)

    # 4. Эмулируем prefetch, как это делает paginated_book_content
    # В реальности prefetch_related('bseries_set') возвращает список объектов bseries
    book.c_authors = []
    book.c_genres = []

    # Создаем объекты, имитирующие bseries (с id серий, как в реальных объектах)
    class MockBSeries:
        def __init__(self, ser_id, ser_name, no):
            self.ser_id = ser_id
            self.ser = type("obj", (object,), {"ser": ser_name})
            self.ser_no = no

    book.c_ser_no = [
        MockBSeries(s1.id, "Series A", 10),
        MockBSeries(s2.id, "Series B", 20),
        MockBSeries(s3.id, "Series C", 30),
    ]

    item = _build_book_item(book)
    description = book_description(item)

    # Ссылка на серию в карточке требует id из данных
    assert item["series"][0]["id"] == s1.id
    assert item["series"][0]["ser"] == "Series A"
    assert item["series"][0]["no"] == 10

    print("\n--- New Description ---")
    print(description)

    # Ожидаем, что серии и номера склеены в одну строку
    # "Series: Series A (10), Series B (20), Series C (30)"
    assert "Series A (10), Series B (20), Series C (30)" in description
    # Проверяем, что старый раздел "No in Series" исчез
    assert "No in Series:" not in description
