from .base import *  # noqa: F403

DEBUG = False

INTERNAL_IPS = ["127.0.0.1"]

ROOT_URLCONF = "sopds.urls.test"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "tmp/db.sqlite3",
    }
}
