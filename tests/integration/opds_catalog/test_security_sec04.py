import pytest
from django.db import transaction

from opds_catalog.models import Book
from opds_catalog.services import scanner
from opds_catalog.services.book_writer import BookWriter, FileSpec


@pytest.mark.django_db
class TestSecuritySEC04:
    def test_existing_book_should_not_be_deleted(self, catalog):
        """SEC-04: Книги, найденные на диске, не должны быть удалены в конце скана."""

        # 1. Подготовка: создаем книгу, которая "уже есть" в базе
        file_spec = FileSpec(
            path="test/path",
            filename="existing_book.fb2",
            rel_path="test/path",
            extension="fb2",
            file_size=1024,
        )

        # Создаем книгу через BookWriter, чтобы она была правильно инициализирована
        writer = BookWriter()
        from opds_catalog.services.dto import BookMetadata

        meta = BookMetadata(
            title="Existing Book",
            annotation="Annotation",
            authors=[],
            genres=[],
            series=[],
            docdate="2023-01-01",
            lang="ru",
        )
        writer.save_book(meta, file=file_spec, catalog=catalog, cat_type=0)

        # Проверяем, что книга создана
        assert Book.objects.filter(filename="existing_book.fb2").exists()

        # 2. Имитируем цикл сканирования
        # Шаг А: Подготовка (все становятся avail=1)
        scanner.avail_check_prepare()
        assert Book.objects.get(filename="existing_book.fb2").avail == 1

        # Шаг Б: Проверка существования (имитация того, что сканер нашел файл на диске)
        # В текущей реализации writer.exists() просто возвращает True, не меняя avail
        exists = writer.exists(file_spec)
        assert exists is True

        # Шаг В: Физическое удаление
        scanner.books_del_phisical()

        # 3. Проверка: книга ДОЛЖНА остаться в базе
        # Если SEC-04 не исправлена, книга будет удалена, и этот assert упадет
        assert Book.objects.filter(filename="existing_book.fb2").exists(), (
            "Book was erroneously deleted despite being present on disk"
        )
