
from django.conf.urls import url

import views

urlpatterns = [
    url(r'^setup/(?P<project_pk>[0-9]+)/$', views.pooled_crispr_setup_view, name='pooled_crispr_setup'),
]
