import pytest
from django.test import RequestFactory

from opds_catalog.models import Counter
from src.sopds_web_backend.processors import sopds_processor


@pytest.mark.django_db
def test_sopds_processor_empty_counter():
    """Проверка, что пустая таблица Counter не вызывает KeyError в процессоре."""
    # Очищаем таблицу Counter
    Counter.objects.all().delete()

    rf = RequestFactory()
    request = rf.get("/")
    request.user = type("User", (), {"is_authenticated": False})()

    try:
        args = sopds_processor(request)
        assert "stats" in args
        assert args["stats"].get("allbooks") is None
        assert args["stats"].get("lastscan_date") is None
        assert args["random_book"] is None
    except KeyError as e:
        pytest.fail(f"Processor crashed with KeyError: {e}")
    except Exception as e:
        pytest.fail(f"Processor crashed with unexpected error: {e}")
