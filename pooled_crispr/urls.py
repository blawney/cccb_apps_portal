
from django.conf.urls import url

import views

urlpatterns = [
    url(r'^upload/(?P<project_pk>[0-9]+)/$', views.pooled_crispr_upload_view, name='pooled_crispr_upload'),
    url(r'^summary/(?P<project_pk>[0-9]+)/$', views.pooled_crispr_summary_view, name='pooled_crispr_summary'),
]
