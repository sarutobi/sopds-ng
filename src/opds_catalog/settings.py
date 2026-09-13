import logging

# from constance import config
from constance.signals import config_updated
from django.conf import settings

# import os
from django.db.backends.signals import connection_created
from django.dispatch import receiver
from django.utils import translation

loglevels = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
    "none": logging.NOTSET,
}
NOZIP_FORMATS = ["epub", "mobi"]

VERSION = getattr(settings, "VERSION", "develop")
TITLE = getattr(settings, "SOPDS_TITLE", "SimpleOPDS NG")
SUBTITLE = getattr(
    settings,
    "SOPDS_SUBTITLE",
    f"SimpleOPDS Catalog new generation by www.sopds-ng.ru. Version {VERSION}",
)
ICON = getattr(settings, "SOPDS_ICON", "/static/images/favicon.ico")
THUMB_SIZE = 300

loglevel = getattr(settings, "SOPDS_LOGLEVEL", "info")
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
