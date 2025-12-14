"""Общие фикстуры для всего проекта"""

import os
from pathlib import Path
import pytest
from tests.opds_catalog.helpers import read_file_as_iobytes
import io


@pytest.fixture
def fake_sopds_root_lib(override_config):
    with override_config(
        SOPDS_ROOT_LIB=os.path.join(
            os.path.dirname(Path(__file__)), "opds_catalog/data/"
        )
    ):
        yield


@pytest.fixture
def test_rootlib() -> str:
    test_module_path: str = os.path.dirname(Path(__file__).resolve())
    test_ROOTLIB = os.path.join(test_module_path, "opds_catalog/data")
    return test_ROOTLIB


@pytest.fixture
def fb2_book_from_fs(test_rootlib) -> io.BytesIO:
    """Предоставляет считанную из ФС книгу в формате FB2"""
    return read_file_as_iobytes(os.path.join(test_rootlib, "262001.fb2"))
