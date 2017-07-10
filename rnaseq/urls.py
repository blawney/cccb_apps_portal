
from django.conf.urls import url

import views

urlpatterns = [
    url(r'^dge/(?P<project_pk>[0-9]+)/$', views.dge_setup_view, name='dge'),
    url(r'^run/(?P<project_pk>[0-9]+)/$', views.perform_dge, name='dge_run'),
]
