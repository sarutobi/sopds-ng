import os
from pathlib import Path

import pytest


@pytest.fixture
def fake_sopds_root_lib(override_config, test_rootlib):
    """Параметр конфигурации 'Корневая директория библиотеки' для тестов"""
    with override_config(SOPDS_ROOT_LIB=test_rootlib):
        yield


@pytest.fixture(scope="session")
def test_rootlib() -> str:
    """Корневая директория библиотеки для тестов"""
    test_module_path: str = os.path.dirname(Path(__file__).parent.resolve())
    test_ROOTLIB = os.path.join(test_module_path, "opds_catalog/data")
    return test_ROOTLIB
