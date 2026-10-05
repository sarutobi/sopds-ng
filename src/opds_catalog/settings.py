import logging

# from opds_catalog.config import catalog_config
from constance.signals import config_updated

# import os
from django.dispatch import receiver
from django.utils import translation

from opds_catalog.config import catalog_config

loglevels = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
    "none": logging.NOTSET,
}
NOZIP_FORMATS = ["epub", "mobi"]

VERSION = catalog_config.VERSION
TITLE = catalog_config.TITLE
SUBTITLE = catalog_config.SUBTITLE
ICON = catalog_config.ICON
THUMB_SIZE = catalog_config.THUMB_SIZE

loglevel = catalog_config.LOGLEVEL
if loglevel.lower() in loglevels:
    LOGLEVEL = loglevels[loglevel.lower()]
else:
    LOGLEVEL = logging.NOTSET


@receiver(config_updated)
def constance_updated(sender, key, new_value, old_value, **kwargs):
    if key == "SOPDS_LANGUAGE":
        translation.activate(new_value)
        # print(new_value)


def constance_update_all():
    pass
