"""Команда импорта справочника жанров из текстового glst-файла."""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from opds_catalog.services.genre_import import import_genres

# Файл ищется в DATA_ROOT, при отсутствии используется встроенный в пакет
PACKAGE_GLS = Path(__file__).resolve().parents[2] / "fixtures" / "genres_fb2.glst"


def default_glst() -> Path:
    """Возвращает путь к справочнику по умолчанию."""
    data_glst = Path(settings.DATA_ROOT) / "genres_fb2.glst"
    if data_glst.is_file():
        return data_glst
    return PACKAGE_GLS


class Command(BaseCommand):
    """Импорт справочника жанров по коду жанра (update_or_create)."""

    help = (
        "Импорт справочника жанров из текстового файла формата glst. "
        "Обновление по коду жанра, привязки книг не затрагиваются."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "glst_file",
            nargs="?",
            default=None,
            help=(
                "Путь к glst-файлу. По умолчанию ищется genres_fb2.glst "
                "в DATA_ROOT, при отсутствии используется встроенный в пакет."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Не вносить изменения в БД, только подсчитать.",
        )
        parser.add_argument(
            "--dump-fixture",
            action="store_true",
            dest="dump_fixture",
            default=False,
            help="Перегенерировать fixtures/genre.json после импорта.",
        )

    def handle(self, *args, **options):
        path = options["glst_file"] or str(default_glst())
        if not Path(path).is_file():
            raise CommandError(f"Файл не найден: {path}")

        created, updated = import_genres(path, dry_run=options["dry_run"])
        mode = " (dry-run)" if options["dry_run"] else ""
        self.stdout.write(
            f"Импорт жанров из {path} завершен{mode}: "
            f"создано {created}, обновлено {updated}."
        )

        if options["dump_fixture"]:
            self.dump_fixture()

    def dump_fixture(self):
        """Сохранение текущего справочника жанров в фикстуру."""
        from django.core.management import call_command

        call_command(
            "dumpdata",
            "opds_catalog.genre",
            "--output",
            "opds_catalog/fixtures/genre.json",
        )
        self.stdout.write("Фикстура сохранена в opds_catalog/fixtures/genre.json")
