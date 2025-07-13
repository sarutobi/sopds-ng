"""
URL configuration for sopds project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls import include
from django.views.generic import RedirectView
from django.urls import reverse_lazy, path

urlpatterns = [
    path('opds/', include('opds_catalog.urls', namespace='opds')),
    path('web/', include('sopds_web_backend.urls', namespace='web')),
    path('admin/', admin.site.urls),
    #url(r'^logout/$', logout, {'next_page':'/web/'},name='logout'),   
    #url(r'^', include('sopds_web_backend.urls', namespace='web', app_name='opds_web_backend')),
    path('', RedirectView.as_view(url=reverse_lazy("web:main"))),
]
