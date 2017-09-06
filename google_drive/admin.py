# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from models import DriveUserCredentials

# Register your models here.
class DriveUserCredentialsAdmin(admin.ModelAdmin):
        list_display = ('owner', 'json_credentials')
        list_editable = ('json_credentials',)

admin.site.register(DriveUserCredentials, DriveUserCredentialsAdmin)
