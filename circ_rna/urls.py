from django.conf.urls import url

import views

urlpatterns = [
    url(r'^upload/(?P<project_pk>[0-9]+)/$', views.circ_rna_fastq_upload, name='circ_rna_fastq_upload'),
    url(r'^summary/(?P<project_pk>[0-9]+)/$', views.circ_rna_summary_view, name='circ_rna_summary'),
]
