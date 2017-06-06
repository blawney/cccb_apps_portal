# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from models import Resource

class ResourceAdmin(admin.ModelAdmin):
        list_display = ('project', 'basename','public_link','resource_type')
        list_editable = ('resource_type',)

admin.site.register(Resource, ResourceAdmin)
