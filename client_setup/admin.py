# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from models import Service,Project,Sample,DataSource, Organism

class ServiceAdmin(admin.ModelAdmin):
	list_display = ('name', 'description', 'application_url', 'upload_instructions')
	list_editable = ('description', 'application_url', 'upload_instructions')

class ProjectAdmin(admin.ModelAdmin):
	list_display = ('name', 'owner','service', 'bucket', 'completed','in_progress', 'paused_for_user_input', 'start_time', 'finish_time', 'reference_organism', 'ilab_id', 'next_action_text', 'next_action_url', 'status_message', 'max_sample_number', 'creation_date')
	list_editable = ('service', 'completed','in_progress', 'paused_for_user_input', 'start_time', 'finish_time', 'reference_organism', 'ilab_id', 'next_action_text', 'next_action_url', 'status_message', 'max_sample_number', 'creation_date')

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
