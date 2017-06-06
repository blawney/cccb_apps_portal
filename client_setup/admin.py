# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from models import Service,Project,Sample,DataSource, Organism

class ServiceAdmin(admin.ModelAdmin):
	list_display = ('name', 'description', 'application_url')
	list_editable = ('description', 'application_url')

class ProjectAdmin(admin.ModelAdmin):
	list_display = ('name', 'owner','service', 'bucket', 'completed','in_progress', 'start_time', 'finish_time', 'reference_organism')
	list_editable = ('service', 'completed','in_progress', 'start_time', 'finish_time', 'reference_organism')

class SampleAdmin(admin.ModelAdmin):
	list_display = ('name','project','processed')
	list_editable = ('project','processed')

class DataSourceAdmin(admin.ModelAdmin):
	list_display = ('sample', 'project','source_type', 'filepath')
	list_editable = ('source_type', 'filepath', 'project')

class OrganismAdmin(admin.ModelAdmin):
	list_display = ('reference_genome', 'description')
	list_editable = ('description',)

admin.site.register(Service, ServiceAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Sample, SampleAdmin)
admin.site.register(DataSource, DataSourceAdmin)
admin.site.register(Organism, OrganismAdmin)
