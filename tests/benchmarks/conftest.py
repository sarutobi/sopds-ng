"""Конфигурация бенчмарков для сканера."""

import pytest


@pytest.fixture
def benchmark_config():
    """Настройки для бенчмарков."""
    return {
        "books_count": 100,  # Количество книг для генерации базовой нагрузки
    }
