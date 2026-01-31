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

SOPDS_SERVER_LOG_LEVEL = "INFO"

# Logger settings
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{levelname} [{name}:{funcName}:{lineno}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": True,
        },
        "opds_catalog": {
            "handlers": ["console"],
            "level": SOPDS_SERVER_LOG_LEVEL,
            "propagate": False,
        },
        "book_tools": {
            "handlers": ["console"],
            "level": SOPDS_SERVER_LOG_LEVEL,
            "propagate": False,
        },
        "scanner": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
