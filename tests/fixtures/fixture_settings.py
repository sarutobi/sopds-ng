import os
from pathlib import Path

import pytest


@pytest.fixture
def fake_sopds_root_lib(override_config, test_rootlib):
    """Параметр конфигурации 'Корневая директория библиотеки' для тестов

    Временно подменяет конфигурационный параметр ``SOPDS_ROOT_LIB`` на значение
    ``test_rootlib`` (через ``override_config``). После теста восстанавливает
    оригинальное значение.

    :scope: function
    :param override_config: фикстура для временной замены конфигурации
    :type override_config: callable
    :param test_rootlib: путь к тестовой директории
    :type test_rootlib: str
    :yields: None
    """
    with override_config(SOPDS_ROOT_LIB=test_rootlib):
        yield


@pytest.fixture(scope="session")
def test_rootlib() -> str:
    """Корневая директория библиотеки для тестов

    Возвращает строку — путь к корневой тестовой директории, где расположены
    файлы книг (``tests/opds_catalog/data``).

    :scope: session
    :returns: путь к тестовой корневой директории
    :rtype: str
    """
    test_module_path: str = str(Path(__file__).parent.parent.resolve())
    test_ROOTLIB = os.path.join(test_module_path, "data")
    return test_ROOTLIB
