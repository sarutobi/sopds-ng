"""Characterization-тест пути INPX.

Фиксирует текущее поведение системы при обработке INPX-коллекций.
"""

import json
import os
from pathlib import Path

import pytest

from opds_catalog.config import catalog_config
from opds_catalog.sopdscan import opdsScanner
from tests.fixtures.fixture_scanner_data import (
    InpRecord,
    make_inpx,
    scanner_boundary_cases,
)


@pytest.mark.django_db
def test_characterize_inpx_baseline(tmp_path, db, monkeypatch, scanner_boundary_cases):
    """Characterization-тест: сравнение текущего состояния с baseline-файлом."""
    # 1. Подготовка данных
    records = [case["inpx"] for case in scanner_boundary_cases if "inpx" in case]
    inpx_bytes = make_inpx(records)

    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    inpx_file = lib_dir / "collection.inpx"
    inpx_file.write_bytes(inpx_bytes)

    # Настройки через monkeypatch на constance_config, так как catalog_config.ROOT_LIB - property без setter
    from opds_catalog.config import constance_config

    monkeypatch.setattr(constance_config, "SOPDS_ROOT_LIB", str(lib_dir))
    monkeypatch.setattr(constance_config, "SOPDS_INPX_ENABLE", True)
    monkeypatch.setattr(constance_config, "SOPDS_INPX_SKIP_UNCHANGED", False)
    monkeypatch.setattr(constance_config, "SOPDS_INPX_TEST_ZIP", False)
    monkeypatch.setattr(constance_config, "SOPDS_INPX_TEST_FILES", False)

    # 2. Запуск конвейера
    scanner_svc = opdsScanner()
    scanner_svc.processinpx("collection.inpx", str(lib_dir), str(inpx_file))

    # 3. Снимок состояния
    from tests.integration.opds_catalog.snapshot import (
        save_snapshot,
        take_full_snapshot,
    )

    stats = {
        "books_added": scanner_svc.books_added,
        "books_skipped": scanner_svc.books_skipped,
        "books_in_archives": scanner_svc.books_in_archives,
        "bad_books": scanner_svc.bad_books,
    }
    snapshot = take_full_snapshot(stats)

    # 4. Верификация
    snapshot_path = Path("tests/integration/opds_catalog/snapshots/inpx_baseline.json")

    if not snapshot_path.exists():
        save_snapshot(snapshot_path, snapshot)
        pytest.fail(
            f"Baseline snapshot created at {snapshot_path}. Please review it and run again."
        )

    with open(snapshot_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    assert snapshot == expected, "Current state differs from baseline"


@pytest.mark.django_db
def test_characterize_inpx_skip_unchanged(
    tmp_path, db, monkeypatch, scanner_boundary_cases
):
    """Проверка влияния INPX_SKIP_UNCHANGED на результат."""
    records = [case["inpx"] for case in scanner_boundary_cases if "inpx" in case]
    inpx_bytes = make_inpx(records)

    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    inpx_file = lib_dir / "collection.inpx"
    inpx_file.write_bytes(inpx_bytes)

    from opds_catalog.config import constance_config

    monkeypatch.setattr(constance_config, "SOPDS_ROOT_LIB", str(lib_dir))
    monkeypatch.setattr(constance_config, "SOPDS_INPX_ENABLE", True)

    scanner_svc = opdsScanner()

    # Первый прогон (создание записей)
    monkeypatch.setattr(constance_config, "SOPDS_INPX_SKIP_UNCHANGED", False)
    scanner_svc.processinpx("collection.inpx", str(lib_dir), str(inpx_file))
    first_added = scanner_svc.books_added

    # Сброс статистики
    scanner_svc.init_stats()

    # Второй прогон с включенным SKIP
    monkeypatch.setattr(constance_config, "SOPDS_INPX_SKIP_UNCHANGED", True)
    scanner_svc.processinpx("collection.inpx", str(lib_dir), str(inpx_file))

    assert scanner_svc.books_added == 0
    assert first_added > 0
