"""Тесты импорта справочника жанров из glst-файла."""

import pytest
from django.core.management import call_command

from opds_catalog.models import Genre, bgenre
from opds_catalog.services.genre_import import import_genres, parse_glst

pytestmark = pytest.mark.django_db

GLST_SAMPLE = """\
#---- Список жанров fb2 ------------------
0.1 Деловая литература
0.1.0 economics_ref;Деловая литература
0.1.1 popular_business;Карьера, кадры

0.2 Детективы и триллеры
0.2.2 det_lady;Дамский детективный роман

0.22 Фантастика
0.22.13 sf_litrpg;ЛитРПГ
0.22.20 popadancy;Попаданцы
"""


class TestParseGlst:
    def test_parse_sample(self):
        """Разбор образца файла."""
        result = parse_glst(GLST_SAMPLE)
        assert result.errors == []
        assert len(result.entries) == 5
        det = next(e for e in result.entries if e.genre == "det_lady")
        assert det.section == "Детективы и триллеры"
        assert det.subsection == "Дамский детективный роман"

    def test_parse_real_file(self):
        """Разбор реального файла справочника."""
        from pathlib import Path

        path = Path(__file__).parents[3] / "src/opds_catalog/fixtures/genres_fb2.glst"
        result = parse_glst(path.read_text(encoding="utf-8"))
        assert result.errors == []
        # В справочнике 272 жанра
        assert len(result.entries) == 272
        # Секции извлекаются из строк-комментариев
        litrpg = next(e for e in result.entries if e.genre == "sf_litrpg")
        assert litrpg.section == "Фантастика"
        assert litrpg.subsection == "ЛитРПГ"
        det = next(e for e in result.entries if e.genre == "det_lady")
        assert det.section == "Детективы и триллеры"
        codes = {e.genre for e in result.entries}
        for code in [
            "popadancy",
            "sf_litrpg",
            "fan_translation",
            "boyar_anime",
            "child_tale_foreign_writers",
            "child_tale_russian_writers",
            "magic_school",
            "sf_realrpg",
            "det_lady",
        ]:
            assert code in codes


class TestImportGenres:
    def test_import_creates_genres(self):
        """Импорт создает жанры с корректными section/subsection."""
        created, updated = import_genres_from_sample()
        assert created == 5
        assert updated == 0

        det = Genre.objects.get(genre="det_lady")
        assert det.section == "Детективы и триллеры"
        assert det.subsection == "Дамский детективный роман"

    def test_import_updates_by_code_not_pk(self):
        """Повторный импорт обновляет по коду жанра, pk сохраняется."""
        # Создаем жанр с "неправильной" секцией, как это делает сканер
        g = Genre.objects.create(
            genre="sf_litrpg", section="Unknown genre", subsection="sf_litrpg"
        )
        pk = g.pk

        import_genres_from_sample()

        g.refresh_from_db()
        assert g.pk == pk
        assert g.section == "Фантастика"
        assert g.subsection == "ЛитРПГ"

    def test_import_does_not_touch_book_links(self, catalog):
        """Привязки книг к жанрам не затрагиваются."""
        g = Genre.objects.create(
            genre="popadancy", section="Unknown genre", subsection="popadancy"
        )
        from opds_catalog.models import Book

        book = Book.objects.create(
            filename="b.fb2",
            path=".",
            format="fb2",
            title="B",
            search_title="B",
            catalog=catalog,
        )
        bgenre.objects.create(book=book, genre=g)
        fk = bgenre.objects.get(book=book).genre_id

        import_genres_from_sample()

        assert bgenre.objects.get(book=book).genre_id == fk

    def test_unknown_genres_untouched(self):
        """Жанры, отсутствующие в справочнике, не изменяются."""
        Genre.objects.create(
            genre="totally_custom", section="Unknown genre", subsection="totally_custom"
        )
        import_genres_from_sample()
        g = Genre.objects.get(genre="totally_custom")
        assert g.section == "Unknown genre"

    def test_dry_run_does_not_write(self):
        """Dry-run не вносит изменения в БД."""
        created, updated = import_genres_from_sample(dry_run=True)
        assert created == 5
        assert updated == 0
        assert Genre.objects.count() == 0

    def test_command(self):
        """Запуск management command."""
        import pathlib
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".glst", delete=False) as f:
            f.write(GLST_SAMPLE)
            path = f.name
        call_command("import_genres", path)
        assert Genre.objects.filter(genre="sf_litrpg").exists()


def import_genres_from_sample(dry_run: bool = False) -> tuple[int, int]:
    """Импорт образца справочника (запись во временный файл)."""
    import pathlib
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".glst", delete=False) as f:
        f.write(GLST_SAMPLE)
        name = f.name
    return import_genres(name, dry_run=dry_run)
