from io import StringIO

import pytest
from constance import config
from django.core.management import call_command

pytestmark = pytest.mark.django_db


class TestConstance:  # integration
    test_module_path = __file__

    def test_constance_attributes_count(self) -> None:
        out = StringIO()
        call_command("constance", "list", stdout=out)
        out.seek(0)
        assert out.getvalue().count("\n") == 37
        out.close()

    def test_constance_set_get_attr(self) -> None:
        conf_value = "test_temp_dir"
        call_command("constance", "set", "SOPDS_TEMP_DIR", conf_value)
        assert config.SOPDS_TEMP_DIR == conf_value
        out = StringIO()
        call_command("constance", "get", "SOPDS_TEMP_DIR", stdout=out)
        out.seek(0)
        assert out.getvalue().strip() == conf_value
        out.close()
