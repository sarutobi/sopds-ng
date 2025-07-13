from .base import *
import socket

DEBUG = True

INSTALLED_APPS += (
    'debug_toolbar',
)

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

ROOT_URLCONF = 'sopds.urls.local'

INTERNAL_IPS = [ '127.0.0.1',]
ip = socket.gethostbyname(socket.gethostname())
INTERNAL_IPS += [ip[:-1] + '1']
