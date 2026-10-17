"""Characterization-тест пути raw_scan.

Фиксирует текущее поведение системы при обработке файлов напрямую (raw_scan).
"""

import json
import zipfile
from pathlib import Path

import pytest

from opds_catalog.config import catalog_config
from opds_catalog.sopdscan import opdsScanner
from tests.book_tools.format.helpers import fb2_book_fabric
from tests.fixtures.fixture_scanner_data import scanner_boundary_cases


@pytest.mark.django_db
def test_characterize_rawscan_baseline(
    tmp_path, db, monkeypatch, scanner_boundary_cases
):
    """Characterization-тест: сравнение текущего состояния с baseline-файлом."""
    # 1. Подготовка данных
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()

    # Создаем набор файлов на основе граничных случаев
    files_to_create = []
    for case in scanner_boundary_cases:
        if case["id"] == "R-13":
            # Для битого файла просто создаем мусор
            file_path = lib_dir / f"bad_{case['id']}.fb2"
            file_path.write_bytes(b"not a real fb2 file")
            files_to_create.append(file_path)
            continue

        if "fb2" in case and isinstance(case["fb2"], dict):
            book_bytes = fb2_book_fabric(**case["fb2"])
            file_path = lib_dir / f"book_{case['id']}.fb2"
            file_path.write_bytes(book_bytes)
            files_to_create.append(file_path)

    # Создаем один ZIP-архив с несколькими книгами для проверки ZIP-режима
    zip_path = lib_dir / "archive.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for case in scanner_boundary_cases[:5]:  # Первые 5 кейсов в архив
            if "fb2" in case and isinstance(case["fb2"], dict):
                book_bytes = fb2_book_fabric(**case["fb2"])
                zf.writestr(f"book_{case['id']}.fb2", book_bytes)

    # Настройки через monkeypatch
    from opds_catalog.config import constance_config

    monkeypatch.setattr(constance_config, "SOPDS_ROOT_LIB", str(lib_dir))
    monkeypatch.setattr(
        constance_config, "SOPDS_INPX_ENABLE", False
    )  # Отключаем INPX, чтобы тестировать raw_scan

    # 2. Запуск конвейера
    scanner_svc = opdsScanner()
    scanner_svc.scan_all()

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
    snapshot_path = Path(
        "tests/integration/opds_catalog/snapshots/rawscan_baseline.json"
    )

    if not snapshot_path.exists():
        save_snapshot(snapshot_path, snapshot)
        pytest.fail(
            f"Baseline snapshot created at {snapshot_path}. Please review it and run again."
        )

    with open(snapshot_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    assert snapshot == expected, "Current state differs from baseline"


@pytest.mark.django_db
def test_characterize_rawscan_idempotency(
    tmp_path, db, monkeypatch, scanner_boundary_cases
):
    """Проверка идемпотентности raw_scan (повторный прогон не должен добавлять книги)."""
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()

    for case in scanner_boundary_cases[:5]:
        if "fb2" in case and isinstance(case["fb2"], dict):
            book_bytes = fb2_book_fabric(**case["fb2"])
            file_path = lib_dir / f"book_{case['id']}.fb2"
            file_path.write_bytes(book_bytes)

    from opds_catalog.config import constance_config

    monkeypatch.setattr(constance_config, "SOPDS_ROOT_LIB", str(lib_dir))
    monkeypatch.setattr(constance_config, "SOPDS_INPX_ENABLE", False)

    scanner_svc = opdsScanner()

    # Первый прогон
    scanner_svc.scan_all()
    first_added = scanner_svc.books_added

    # Второй прогон
    scanner_svc.init_stats()
    scanner_svc.scan_all()

    assert scanner_svc.books_added == 0
    assert scanner_svc.books_skipped > 0
    assert first_added > 0
