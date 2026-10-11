"""Низкоуровневые утилиты работы с БД."""

from django.db import connection, transaction


def ensure_pg_trgm_index():
    """Установка расширения pg_trgm и создание GIN-индекса по названию книги.

    Используется для ускорения поиска подстрок (ILIKE '%...%') по полю title.
    """
    with connection.cursor() as cursor:
        cursor.execute("select count(*) from pg_extension where extname='pg_trgm'")
        row = cursor.fetchone()
        if row and row[0] == 0:
            cursor.execute("create extension pg_trgm")
            cursor.execute(
                "create index concurrently opds_catalog_book_title_gin_idx on opds_catalog_book using gin (title gin_trgm_ops)"
            )


def pg_optimize(verbose=False):
    """Оптимизация таблиц для Postgres."""
    if connection.vendor != "postgresql":
        if verbose:
            print("No PostgreSql connection backend detected...")
        return

    print("Start PostgreSql tables optimization...")
    with connection.cursor() as cursor:
        cursor.execute("alter table opds_catalog_book SET ( fillfactor = 100)")
    ensure_pg_trgm_index()
    print("PostgreSql tables internal structure optimized...")


def clear_all(verbose=False):
    """Полная очистка всех таблиц каталога."""
    with connection.cursor() as cursor:
        tables = [
            "opds_catalog_bseries",
            "opds_catalog_bauthor",
            "opds_catalog_bgenre",
            "opds_catalog_bookshelf",
            "opds_catalog_book",
            "opds_catalog_catalog",
            "opds_catalog_author",
            "opds_catalog_genre",
            "opds_catalog_series",
            "opds_catalog_counter",
        ]
        for table in tables:
            cursor.execute(f"delete from {table}")


def clear_genres(verbose=False):
    """Очистка таблицы жанров."""
    with connection.cursor() as cursor:
        cursor.execute("delete from opds_catalog_genre")


def seed_constance_defaults() -> int:
    """Материализация строк constance с дефолтными значениями.

    Constance DatabaseBackend вставляет строку с дефолтом при первом обращении
    к ключу. Если это происходит внутри долгой транзакции (например, скана
    библиотеки), параллельные веб-запросы, читающие те же ключи, блокируются
    на уникальном индексе до коммита. Функция создает все ключи заранее
    в отдельной короткой транзакции.

    :returns: Количество созданных строк.
    """
    from constance import config as constance_config
    from constance.models import Constance
    from django.conf import settings as constance_settings

    before = Constance.objects.count()
    with transaction.atomic():
        # Обращение к ключу через config заставляет DatabaseBackend
        # вставить строку с корректным дефолтом
        for key in constance_settings.CONSTANCE_CONFIG:
            getattr(constance_config, key)
    return Constance.objects.count() - before
