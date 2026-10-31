"""Утилита канонического снимка состояния БД для сканера.

Используется для characterization-тестов и parity-тестов.
"""

import json
from pathlib import Path
from typing import Any

from django.db.models import Model


def get_model_snapshot(
    model_class: type[Model], filters: dict[str, Any] = None
) -> list[dict]:
    """Создаёт список словарей из объектов модели, исключая volatile-поля.

    Поля 'id' и 'registerdate' исключаются, так как они меняются при каждом прогоне.
    """
    qs = model_class.objects.all()
    if filters:
        qs = qs.filter(**filters)

    # Сортировка по бизнес-ключам для детерминизма
    if hasattr(model_class, "full_name"):  # Author
        qs = qs.order_by("full_name", "id")
    elif hasattr(model_class, "title"):  # Book
        qs = qs.order_by("title", "filename", "path", "id")
    elif hasattr(model_class, "cat_name"):  # Catalog
        qs = qs.order_by("cat_name", "path", "id")
    elif hasattr(model_class, "genre"):  # Genre
        qs = qs.order_by("genre", "id")
    elif hasattr(model_class, "ser"):  # Series
        qs = qs.order_by("ser", "id")
    elif model_class.__name__ == "bauthor":
        qs = qs.order_by("author__full_name", "book__title", "book__filename", "id")
    elif model_class.__name__ == "bgenre":
        qs = qs.order_by("genre__genre", "book__title", "book__filename", "id")
    elif model_class.__name__ == "bseries":
        qs = qs.order_by("ser__ser", "book__title", "book__filename", "id")
    else:
        qs = qs.order_by("id")

    snapshot = []
    for obj in qs:
        data = {}
        # Получаем все поля модели
        for field in obj._meta.fields:
            name = field.name
            if name in ("id", "registerdate"):
                continue
            val = getattr(obj, name)
            # Обработка связей для детерминизма
            if hasattr(val, "id") and val is not None:
                # Пытаемся найти бизнес-ключ для связи
                if hasattr(val, "full_name"):
                    data[name] = val.full_name
                elif hasattr(val, "path"):
                    data[name] = val.path
                elif hasattr(val, "genre"):
                    data[name] = val.genre
                elif hasattr(val, "ser"):
                    data[name] = val.ser
                elif hasattr(val, "title"):
                    data[name] = val.title
                else:
                    data[name] = val.id  # Фоллбэк на ID, если бизнес-ключа нет
            else:
                data[name] = str(val) if val is not None else None
        snapshot.append(data)
    return snapshot


def save_snapshot(path: Path, data: dict[str, Any]):
    """Сохраняет снимок в JSON файл с детерминированной сортировкой."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


def take_full_snapshot(stats: dict[str, Any] = None) -> dict[str, Any]:
    """Собирает полный снимок всех сущностей, задействованных в сканировании."""
    from opds_catalog.models import (
        Author,
        Book,
        Catalog,
        Genre,
        Series,
        bauthor,
        bgenre,
        bseries,
    )

    return {
        "stats": stats or {},
        "books": get_model_snapshot(Book),
        "authors": get_model_snapshot(Author),
        "genres": get_model_snapshot(Genre),
        "series": get_model_snapshot(Series),
        "catalogs": get_model_snapshot(Catalog),
        "bauthors": get_model_snapshot(bauthor),
        "bgenres": get_model_snapshot(bgenre),
        "bseries": get_model_snapshot(bseries),
    }
