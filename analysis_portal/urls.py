
from django.conf.urls import url

import setup_views
import other_views

urlpatterns = [
    url(r'^home/', setup_views.home_view, name='analysis_home_view'),
    url(r'^upload/(?P<project_pk>[0-9]+)/$', setup_views.upload_page),
    url(r'^edit-name/(?P<project_pk>[0-9]+)/$', setup_views.change_project_name),
    url(r'^update-files/(?P<project_pk>[0-9]+)/$', setup_views.add_new_file),
    url(r'^delete-file/(?P<project_pk>[0-9]+)/$', setup_views.delete_file),
    url(r'^annotate-files/(?P<project_pk>[0-9]+)/$', setup_views.annotate_files_and_samples),
    url(r'^genome-choice/(?P<project_pk>[0-9]+)/$', setup_views.genome_selection_page, name='choose_genome'),
    url(r'^set-genome/(?P<project_pk>[0-9]+)/$', setup_views.set_genome, name='set_genome'),
    url(r'^map-files/(?P<project_pk>[0-9]+)/$', setup_views.map_files_to_samples),
    url(r'^summary/(?P<project_pk>[0-9]+)/$', setup_views.summary),
    url(r'^create-sample/(?P<project_pk>[0-9]+)/$', setup_views.create_sample),
    url(r'^remove-sample/(?P<project_pk>[0-9]+)/$', setup_views.rm_sample),
    url(r'^notify/', other_views.notify),
    url(r'^do-analysis/(?P<project_pk>[0-9]+)/$', setup_views.kickoff),
    url(r'^progress/(?P<project_pk>[0-9]+)/$', other_views.show_in_progress, name='in_progress_view'),
    url(r'^complete/(?P<project_pk>[0-9]+)/$', other_views.show_complete, name='complete_view'),
]
