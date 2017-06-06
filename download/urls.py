
from django.conf.urls import url

import views

urlpatterns = [
    url(r'^(?P<project_pk>[0-9]+)/$', views.download_view, name='download_view'),
]
