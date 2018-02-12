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
import dropbox_utils

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^_ah/health', views.health_check),
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
    #url(r'^drive', include('google_drive.urls')),
    url(r'^cleanup/', include('cleanup.urls')),
    #url(r'^drive/', views.drive_test, name='drive_view'),
    #url(r'^drive-callback/', views.oauth2_drive_callback, name='drive_callback'),
     url(r'dbx-file-register', dropbox_utils.register_files_to_transfer),
    url(r'^dbx-callback/', dropbox_utils.dropbox_callback),
    url(r'^dbx/', dropbox_utils.dropbox_auth),
    url(r'dropbox-transfer-complete', dropbox_utils.dropbox_transfer_complete),
    url(r'^pooled-crispr/', include('pooled_crispr.urls')),
    url(r'^circ-rna/', include('circ_rna.urls')),
]
