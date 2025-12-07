"""Общие фикстуры для всего проекта"""

import os
from pathlib import Path
import pytest


@pytest.fixture
def fake_sopds_root_lib(override_config):
    with override_config(
        SOPDS_ROOT_LIB=os.path.join(
            os.path.dirname(Path(__file__)), "opds_catalog/data/"
        )
    ):
        yield
