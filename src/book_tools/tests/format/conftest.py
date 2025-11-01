import pytest
import os
from pathlib import Path
from book_tools.format.fb2sax import fb2tag


@pytest.fixture
def test_tag() -> fb2tag:
    return fb2tag(("description", "title-info", "author", "first-name"))


@pytest.fixture
def test_rootlib() -> str:
    test_module_path: str = os.path.dirname(
        os.path.dirname(Path(__file__).resolve().parent.parent)
    )
    test_ROOTLIB = os.path.join(test_module_path, "opds_catalog/tests/data")
    return test_ROOTLIB
