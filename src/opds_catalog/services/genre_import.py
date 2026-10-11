"""Импорт справочника жанров из текстового файла формата glst.

Формат файла (см. fixtures/genres_fb2.glst):
    # комментарий
    0.1 Деловая литература              <- заголовок группы, задает section
    0.1.0 economics_ref;Деловая литература  <- жанр: код;название (subsection)
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from django.db import transaction

from opds_catalog.models import Genre

# Жанр: "0.2.2 det_lady;Дамский детективный роман"
GENRE_RE = re.compile(r"^[\d.]+\s+(\S+);(.+)$")
# Заголовок группы: "0.2 Детективы и триллеры" (в т.ч. внутри комментария
# вида "#------ 0.1 Деловая литература ---------------------------")
SECTION_RE = re.compile(r"^\d+\.\d+\s+(.+)$")
COMMENT_DECOR_RE = re.compile(r"^#+\s*-*\s*|\s*-+\s*$")


@dataclass
class GenreEntry:
    """Запись справочника жанров."""

    genre: str
    section: str
    subsection: str


@dataclass
class ParseResult:
    """Результат разбора glst-файла."""

    entries: list[GenreEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def parse_glst(content: str) -> ParseResult:
    """Разбор текстового справочника жанров.

    :param content: Содержимое файла.
    :returns: Список жанров и список ошибок разбора.
    """
    result = ParseResult()
    section = ""
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        # Заголовок группы может быть в комментарии:
        # "#------ 0.1 Деловая литература ---------------------------"
        if line.startswith("#"):
            cleaned = COMMENT_DECOR_RE.sub("", line).strip()
            match = SECTION_RE.match(cleaned)
            if match and ";" not in cleaned:
                section = match.group(1).strip()
            continue
        if ";" in line:
            match = GENRE_RE.match(line)
            if match is None:
                result.errors.append(line)
                continue
            code, name = match.group(1), match.group(2).strip()
            if not section:
                result.errors.append(f"genre without section: {line}")
                continue
            result.entries.append(
                GenreEntry(genre=code, section=section, subsection=name)
            )
        else:
            match = SECTION_RE.match(line)
            if match is None:
                result.errors.append(line)
                continue
            section = match.group(1).strip()
    return result


def import_genres(path: str | Path, dry_run: bool = False) -> tuple[int, int]:
    """Импорт справочника жанров в БД.

    Обновление выполняется по коду жанра (поле genre), а не по pk,
    поэтому безопасно для БД, отсканированной без справочника.
    Привязки книг к жанрам (bgenre) не затрагиваются.

    :param path: Путь к glst-файлу.
    :param dry_run: Не вносить изменения в БД, только подсчитать.
    :returns: Количество созданных и обновленных жанров.
    """
    content = Path(path).read_text(encoding="utf-8")
    parsed = parse_glst(content)

    max_genre = Genre._meta.get_field("genre").max_length
    max_section = Genre._meta.get_field("section").max_length
    max_subsection = Genre._meta.get_field("subsection").max_length

    created_count = 0
    updated_count = 0
    with transaction.atomic():
        for entry in parsed.entries:
            values = {
                "section": entry.section[:max_section],
                "subsection": entry.subsection[:max_subsection],
            }
            if dry_run:
                created = not Genre.objects.filter(
                    genre=entry.genre[:max_genre]
                ).exists()
            else:
                _, created = Genre.objects.update_or_create(
                    genre=entry.genre[:max_genre], defaults=values
                )
            if created:
                created_count += 1
            else:
                updated_count += 1
    return created_count, updated_count
