
from django.conf.urls import url

import views

urlpatterns = [
    url(r'^query-projects/$', views.cleanup, name='cleanup_query'),
]
