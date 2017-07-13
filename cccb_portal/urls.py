"""cccb_portal URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.auth import views as auth_views

import views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^cccb-admin/', include('client_setup.urls')),
    url(r'^$', views.index),
    url(r'^analysis/', include('analysis_portal.urls')),
    url(r'^upload/', include('uploader.urls')),
    url(r'^unauthorized/', views.unauthorized, name='unauthorized'),
    url(r'^callback/', views.oauth2_callback),
    url(r'^login/', views.login),
    url(r'^google-login/', views.google_login),
    url(r'^download/', include('download.urls')),
    url(r'^rnaseq/', include('rnaseq.urls')),
    url(r'^drive/', views.drive_test, name='drive_view'),
    url(r'^drive-callback/', views.oauth2_drive_callback, name='drive_callback'),
    url(r'^dbx-callback/', views.oauth2_dropbox_callback),
    url(r'^dbx/', views.dropbox_test),
    url(r'^dummy/', views.dummy_view),
]
