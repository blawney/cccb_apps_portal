from django.conf.urls import url

import views

urlpatterns = [
    url(r'^sign-url/(?P<project_pk>[0-9]+)/$', views.sign_url, name='url_sign'),
    url(r'^dropbox-transfer/(?P<project_pk>[0-9]+)/$', views.dropbox_transfer, name='dropbox_transfer')
]
