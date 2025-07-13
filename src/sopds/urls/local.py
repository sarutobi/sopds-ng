from django.contrib import admin
from django.conf.urls import include
from django.views.generic import RedirectView
from django.urls import reverse_lazy, path
from debug_toolbar.toolbar import debug_toolbar_urls

from .base import urlpatterns

urlpatterns += debug_toolbar_urls()
