"""Бенчмарки производительности сканера.

Измеряют время выполнения scan_all() и количество SQL-запросов.
"""

import time
from pathlib import Path

import pytest
from django.db import connection

from opds_catalog.config import constance_config
from opds_catalog.sopdscan import opdsScanner
from tests.fixtures.fixture_scanner_data import InpRecord, make_inpx


class QueryCounter:
    """Простой счетчик SQL-запросов."""

    def __enter__(self):
        self.start_queries = len(connection.queries)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_queries = len(connection.queries)
        self.count = self.end_queries - self.start_queries


@pytest.fixture
def run_scan_benchmark(tmp_path, monkeypatch, benchmark_config):
    """
    Фикстура для проведения замера производительности полного цикла scan_all().
    """
    # 1. Подготовка данных (N книг в INPX)
    books_count = benchmark_config["books_count"]
    records = [
        InpRecord(
            title=f"Book {i}",
            author=[f"Author {i}"],
            genre=[f"Genre {i % 10}"],
            file=f"book_{i}.fb2",
        )
        for i in range(books_count)
    ]
    inpx_bytes = make_inpx(records)

    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    inpx_file = lib_dir / "collection.inpx"
    inpx_file.write_bytes(inpx_bytes)

    # Настройки
    monkeypatch.setattr(constance_config, "SOPDS_ROOT_LIB", str(lib_dir))
    monkeypatch.setattr(constance_config, "SOPDS_INPX_ENABLE", True)
    monkeypatch.setattr(constance_config, "SOPDS_INPX_SKIP_UNCHANGED", False)

    scanner_svc = opdsScanner()

    # Замеряем время и запросы для первого прогона (заполнение)
    with QueryCounter() as qc:
        start_time = time.perf_counter()
        scanner_svc.scan_all()
        end_time = time.perf_counter()

    first_pass_time = end_time - start_time
    first_pass_queries = qc.count

    # Замеряем время и запросы для повторного прогона (идемпотентность/кэш)
    scanner_svc.init_stats()
    with QueryCounter() as qc_repeat:
        start_time_rep = time.perf_counter()
        scanner_svc.scan_all()
        end_time_rep = time.perf_counter()

    repeat_pass_time = end_time_rep - start_time_rep
    repeat_pass_queries = qc_repeat.count

    return {
        "books_count": books_count,
        "first_pass": {"time": first_pass_time, "queries": first_pass_queries},
        "repeat_pass": {"time": repeat_pass_time, "queries": repeat_pass_queries},
    }


@pytest.mark.django_db
def test_scan_performance_baseline(run_scan_benchmark):
    """Запуск бенчмарка и верификация того, что он отработал."""
    results = run_scan_benchmark
    assert results["books_count"] == 100
    assert results["first_pass"]["queries"] > 0


@pytest.mark.django_db
def test_benchmark_results_capture(run_scan_benchmark):
    """Запись результатов в baseline.md."""
    results = run_scan_benchmark

    log_dir = Path("logs/book-writer-service")
    log_dir.mkdir(parents=True, exist_ok=True)
    baseline_file = log_dir / "baseline.md"

    with open(baseline_file, "a", encoding="utf-8") as f:
        f.write(f"\n### Run {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- Books: {results['books_count']}\n")
        f.write(
            f"- First pass: {results['first_pass']['time']:.4f}s, {results['first_pass']['queries']} queries\n"
        )
        f.write(
            f"- Repeat pass: {results['repeat_pass']['time']:.4f}s, {results['repeat_pass']['queries']} queries\n"
        )

    assert True
