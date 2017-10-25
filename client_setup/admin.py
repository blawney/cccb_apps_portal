# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from models import Service,Project,Sample, SampleDataSource, DataSource, Organism, Workflow

class ServiceAdmin(admin.ModelAdmin):
	list_display = ('name', 'description', 'application_url')
	list_editable = ('description', 'application_url',)

class ProjectAdmin(admin.ModelAdmin):
	list_display = ('name', 'owner','service', 'bucket', 'completed','in_progress', 'paused_for_user_input', 'start_time', 'finish_time', 'reference_organism', 'ilab_id', 'next_action_text', 'next_action_url', 'status_message', 'max_sample_number', 'creation_date')
	list_editable = ('service', 'completed','in_progress', 'paused_for_user_input', 'start_time', 'finish_time', 'reference_organism', 'ilab_id', 'next_action_text', 'next_action_url', 'status_message', 'max_sample_number', 'creation_date')

class SampleAdmin(admin.ModelAdmin):
	list_display = ('name','project','processed')
	list_editable = ('project','processed')

class DataSourceAdmin(admin.ModelAdmin):
	list_display = ('project','source_type', 'filepath')
	list_editable = ('source_type', 'filepath')

class SampleDataSourceAdmin(admin.ModelAdmin):
	list_display = ('sample', 'project','source_type', 'filepath')
	list_editable = ('source_type', 'filepath', 'project')

class OrganismAdmin(admin.ModelAdmin):
	list_display = ('reference_genome', 'description', 'service')
	list_editable = ('description', 'service')

class WorkflowAdmin(admin.ModelAdmin):
	list_display = ('step_order','step_url', 'service', 'instructions')
	list_editable = ('step_url',)

admin.site.register(Service, ServiceAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Sample, SampleAdmin)
admin.site.register(DataSource, DataSourceAdmin)
admin.site.register(SampleDataSource, SampleDataSourceAdmin)
admin.site.register(Organism, OrganismAdmin)
admin.site.register(Workflow, WorkflowAdmin)
