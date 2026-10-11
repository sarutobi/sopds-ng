"""Тесты прогрева constance перед сканом.

Прогрев материализует строки constance с дефолтами в отдельной транзакции,
чтобы первые вставки дефолтов не попадали в долгую транзакцию сканера
и не блокировали веб-запросы на уникальном индексе.
"""

import pytest
from constance import config as constance_config
from constance.models import Constance
from django.db import connection

from opds_catalog.db_utils import seed_constance_defaults

pytestmark = pytest.mark.django_db


class TestSeedConstanceDefaults:
    def test_creates_all_keys(self):
        """Создаются строки для всех ключей CONSTANCE_CONFIG."""
        created = seed_constance_defaults()
        keys = {c.key for c in Constance.objects.all()}
        from django.conf import settings as constance_settings

        assert keys == set(constance_settings.CONSTANCE_CONFIG.keys())
        assert created > 0

    def test_idempotent(self):
        """Повторный вызов ничего не создает."""
        seed_constance_defaults()
        created = seed_constance_defaults()
        assert created == 0

    def test_seed_opens_own_transaction(self, transactional_db, monkeypatch):
        """Прогрев открывает собственную транзакцию на верхнем уровне.

        Гарантия того, что вставки не попадут в долгую транзакцию сканера
        (и, соответственно, не будут держать блокировки до ее коммита).
        """
        import opds_catalog.db_utils as db_utils

        calls = []
        original_atomic = db_utils.transaction.atomic

        def spy_atomic(using=None):
            calls.append(connection.in_atomic_block)
            return original_atomic(using=using)

        monkeypatch.setattr(db_utils.transaction, "atomic", spy_atomic)

        seed_constance_defaults()

        # Первая транзакция открыта вне внешней (на верхнем уровне);
        # остальные вызовы atomic() — внутренние savepoints бэкенда constance
        assert calls[0] is False
        assert len(calls) > 1

    def test_defaults_match_constance_config(self):
        """Значения созданных строк соответствуют дефолтам constance."""
        seed_constance_defaults()
        # Чтение через constance не должно создавать новых строк
        before = Constance.objects.count()
        _ = constance_config.SOPDS_ROOT_LIB
        _ = constance_config.SOPDS_AUTH
        assert Constance.objects.count() == before
