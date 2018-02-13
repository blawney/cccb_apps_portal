
from django.conf.urls import url

import views

urlpatterns = [
    url(r'^query-projects/$', views.cleanup, name='cleanup_query'),
    url(r'^rm-projects/$', views.remove_projects, name='rm_query'),
]
