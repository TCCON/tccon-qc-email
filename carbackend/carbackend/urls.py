"""carbackend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
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
from django.conf import settings
from django.contrib import admin
from django.http.response import Http404
from django.urls import path, include
from django.shortcuts import redirect

def _redirect_index(request):
    if settings.ENABLE_SITE_STATUS:
        return redirect('opstat/')
    elif settings.ENABLE_SITE_METADATA:
        return redirect('siteinfo/')
    else:
        raise Http404('No part of the site is enabled')


# This Django portal runs on different systems, each of which need a different
# app. To keep one login for both, we use the same Django code, but disable URL
# resolution for the part that we don't use on this system.
urlpatterns = []
if settings.ENABLE_SITE_STATUS:
    urlpatterns.append(path('opstat/', include('opstat.urls')))
if settings.ENABLE_SITE_METADATA:
    urlpatterns.append(path('siteinfo/', include('siteinfo.urls')))
    urlpatterns.append(path('qcform/', include('qcform.urls')))
if settings.ENABLE_SITE_STATUS or settings.ENABLE_SITE_METADATA:
    urlpatterns.extend([
        path('', _redirect_index),
        path('admin/', admin.site.urls),
        path('accounts/', include('django.contrib.auth.urls')),
    ])

