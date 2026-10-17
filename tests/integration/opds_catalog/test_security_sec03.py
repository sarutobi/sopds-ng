import pytest
from django.db import DataError, IntegrityError

from opds_catalog.models import SIZE_BOOK_TITLE, Book, Catalog
from opds_catalog.services.book_writer import BookWriter, FileSpec
from opds_catalog.services.dto import BookMetadata


@pytest.mark.django_db
class TestSecuritySEC03:
    def test_overlong_fields_should_be_truncated(self, catalog):
        """SEC-03: Поля, превышающие max_length, должны быть усечены без падения БД."""
        writer = BookWriter()

        # Создаем метаданные с гигантским заголовком и аннотацией
        meta = BookMetadata(
            title="A" * 5000,
            annotation="B" * 20000,
            authors=[],
            genres=[],
            series=[],
            docdate="2023-01-01",
            lang="ru",
        )
        file_spec = FileSpec(
            path="test/path",
            filename="test.fb2",
            rel_path="test/path",
            extension="fb2",
            file_size=1024,
        )

        # Сейчас это должно упасть либо при создании, либо при save()
        # Если БД SQLite, она может проглотить длину, но Postgres выкинет DataError
        try:
            writer.save_book(meta, file=file_spec, catalog=catalog, cat_type=0)
        except (DataError, IntegrityError, Exception) as e:
            pytest.fail(f"save_book failed with {type(e).__name__}: {e}")

        book = Book.objects.get(filename="test.fb2")
        assert len(book.title) <= SIZE_BOOK_TITLE
        assert len(book.annotation) <= 10000

    def test_empty_title_fallback(self, catalog):
        """SEC-03: При пустом title должен использоваться filename."""
        writer = BookWriter()

        meta = BookMetadata(
            title="",
            annotation="Some annotation",
            authors=[],
            genres=[],
            series=[],
            docdate="2023-01-01",
            lang="ru",
        )
        file_spec = FileSpec(
            path="test/path",
            filename="my_cool_book.fb2",
            rel_path="test/path",
            extension="fb2",
            file_size=1024,
        )

        writer.save_book(meta, file=file_spec, catalog=catalog, cat_type=0)

        book = Book.objects.get(filename="my_cool_book.fb2")
        assert book.title == "my_cool_book.fb2"

    def test_non_bmp_characters(self, catalog):
        """SEC-03: Символы вне BMP должны быть удалены/заменены."""
        writer = BookWriter()

        # Эмодзи (🚀) находится вне BMP
        title_with_emoji = "Книга 🚀"
        meta = BookMetadata(
            title=title_with_emoji,
            annotation="Annotation",
            authors=[],
            genres=[],
            series=[],
            docdate="2023-01-01",
            lang="ru",
        )
        file_spec = FileSpec(
            path="test/path",
            filename="emoji.fb2",
            rel_path="test/path",
            extension="fb2",
            file_size=1024,
        )

        writer.save_book(meta, file=file_spec, catalog=catalog, cat_type=0)

        book = Book.objects.get(filename="emoji.fb2")
        # Ожидаем, что эмодзи будет удален функцией p()
        assert "🚀" not in book.title
