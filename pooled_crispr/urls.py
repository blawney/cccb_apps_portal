from django.conf.urls import url

import views
import analysis.setup_views as analysi_setup_views

urlpatterns = [
    url(r'^upload/(?P<project_pk>[0-9]+)/$', views.pooled_crispr_fastq_upload, name='pooled_crispr_fastq_upload'),
    url(r'^library/(?P<project_pk>[0-9]+)/$', views.pooled_crispr_library_upload, name='pooled_crispr_library_upload'),
    url(r'^summary/(?P<project_pk>[0-9]+)/$', views.pooled_crispr_summary_view, name='pooled_crispr_summary'),
]
