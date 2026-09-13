"""Низкоуровневые утилиты работы с БД."""

from django.db import connection

from opds_catalog.models import Book


def pg_optimize(verbose=False):
    """Оптимизация таблиц для Postgres."""
    if connection.vendor != "postgresql":
        if verbose:
            print("No PostgreSql connection backend detected...")
        return

    print("Start PostgreSql tables optimization...")
    with connection.cursor() as cursor:
        cursor.execute("alter table opds_catalog_book SET ( fillfactor = 100)")
        cursor.execute("VACUUM FULL opds_catalog_book")
        cursor.execute("select count(*) from pg_extension where extname='pg_trgm'")
        row = cursor.fetchone()
        if row and row[0] == 0:
            cursor.execute("create extension pg_trgm")
            cursor.execute(
                "create index concurrently opds_catalog_book_title_gin_idx on opds_catalog_book using gin (title gin_trgm_ops)"
            )
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
