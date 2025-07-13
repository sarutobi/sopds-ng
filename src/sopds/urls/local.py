from django.contrib import admin
from django.conf.urls import include
from django.views.generic import RedirectView
from django.urls import reverse_lazy, path
from debug_toolbar.toolbar import debug_toolbar_urls

from .base import urlpatterns

#urlpatterns = [
#    path('opds/', include('opds_catalog.urls', namespace='opds')),
#    path('web/', include('sopds_web_backend.urls', namespace='web')),
#    path('admin/', admin.site.urls),
#    #url(r'^logout/$', logout, {'next_page':'/web/'},name='logout'),   
#    #url(r'^', include('sopds_web_backend.urls', namespace='web', app_name='opds_web_backend')),
#    path('', RedirectView.as_view(url=reverse_lazy("web:main"))),
#] + debug_toolbar_urls()

urlpatterns += debug_toolbar_urls()
