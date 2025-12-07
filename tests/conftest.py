"""Общие фикстуры для всего проекта"""

import pytest
import os
from constance import config
from django.conf import settings


@pytest.fixture
def manage_sopds_root_lib():
    backup = config.SOPDS_ROOT_LIB
    config.SOPDS_ROOT_LIB = os.path.join(settings.BASE_DIR, "opds_catalog/tests/data/")
    yield config
    config.SOPDS_ROOT_LIB = backup
