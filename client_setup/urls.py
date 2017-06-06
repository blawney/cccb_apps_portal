from django.conf.urls import url

import views

urlpatterns = [
    url(r'client-setup', views.setup_client, name='client_setup'),
]
