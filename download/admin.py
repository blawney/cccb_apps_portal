# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from models import Resource, DropboxTransferMaster, DropboxFileTransfer, ResourceDownload

class ResourceAdmin(admin.ModelAdmin):
        list_display = ('project', 'basename','public_link','resource_type')
        list_editable = ('resource_type',)

class DropboxTransferMasterAdmin(admin.ModelAdmin):
	list_display = ('start_time','name', 'owner')
	list_editable = ('name',)

class DropboxFileTransferAdmin(admin.ModelAdmin):
	list_display = ('master', 'source', 'is_complete')

class ResourceDownloadAdmin(admin.ModelAdmin):
	list_display = ('resource','downloader','download_date')

admin.site.register(Resource, ResourceAdmin)
admin.site.register(ResourceDownload, ResourceDownloadAdmin)
admin.site.register(DropboxTransferMaster, DropboxTransferMasterAdmin)
admin.site.register(DropboxFileTransfer, DropboxFileTransferAdmin)
