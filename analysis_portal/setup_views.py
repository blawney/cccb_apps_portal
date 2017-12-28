# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
import json
import os
import re

from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from client_setup.models import Project, Sample, DataSource, Organism, SampleDataSource
from django.core.exceptions import ObjectDoesNotExist

import sys
sys.path.append(os.path.abspath('..'))
from rnaseq import rnaseq_process
from variant_calling_from_fastq import variant_process_submission_from_fastq
from variant_calling_from_bam import variant_process_submission_from_bam
from pooled_crispr import pooled_crispr_process
from circ_rna import circ_rna_process

import helpers

class ProjectDisplay(object):
	"""
	A simple container class used when displaying the project in the UI
	"""
	def __init__(self, pk, name, service, completed, in_progress, paused, finish_time, status_message, next_action_text, next_action_url, has_downloads, download_url):
		self.pk = pk
		self.name = name
		self.service = service
		self.completed = completed
		self.in_progress = in_progress
		self.paused = paused
		self.status_message = status_message
		self.next_action_text = next_action_text
		self.next_action_url = next_action_url
		self.download_url = download_url
		self.has_downloads = has_downloads
		if finish_time:
			self.finish_time = finish_time.strftime('%b %d, %Y (%H:%M)')
		else:
			self.finish_time = '-'


class FileDisplay(object):
	"""
	A simple container class used to display file details in the UI
	"""
	def __init__(self, samplename, pk, filepath):
		self.samplename = samplename
		self.pk = pk
		self.file_string = os.path.basename(filepath)


@login_required
def set_genome(request, project_pk):
	"""
	Called (by ajax) when setting the selecting/setting the reference genome
	"""
	project = helpers.check_ownership(project_pk, request.user)
	print 'back in set_genome, project=%s' % project
	if project is not None:
		selected_genome = request.POST.get('selected_genome')
		org = Organism.objects.get(reference_genome = selected_genome)
		project.reference_organism = org
		project.save()
		return HttpResponse('')
	else:
		return HttpResponseBadRequest('')


@login_required
def genome_selection_page(request, project_pk):
	"""
	Sets up the page where users select their reference genome
	"""
	project = helpers.check_ownership(project_pk, request.user)
	if project is not None:
		# get the service type which informs which genomes to present
		service = project.service
		d = {}
		orgs = service.organism_set.all() # the references associated with the service
		for org in orgs:
			d[org.reference_genome] = org.description

		previous_url, next_url = helpers.get_bearings(project)
		context = {'project_pk': project.pk, \
				'references':d, \
				'project_name':project.name, \
				'previous_page_url':previous_url, \
				'next_page_url':next_url}
		return render(request, 'analysis_portal/choose_genome.html', context)
	else:
		return HttpResponseBadRequest('')



@login_required
def home_view(request):
	"""
	Displays all the projects
	"""
	context = {}
	user = request.user
	users_projects = Project.objects.filter(owner=user)

	# format the time
	projects = []
	for p in users_projects:
		download_url = reverse('download_view', kwargs={'project_pk':p.pk})
		next_action_url = p.next_action_url # note that the next_action_url is different than the workflow step-based URLs
		projects.append(ProjectDisplay(p.pk, p.name, p.service.description, p.completed, p.in_progress, p.paused_for_user_input, p.finish_time, p.status_message, p.next_action_text, next_action_url, p.has_downloads, download_url))

	context['projects'] = projects
	return render(request, 'analysis_portal/home.html', context)


@login_required
def upload_page(request, project_pk):
	"""
	This fills out the upload page
	"""
	project = helpers.check_ownership(project_pk, request.user)
	if project is not None:
		service = project.service
		view_name = request.resolver_match.url_name
		current_workflow_step = service.workflow_set.get(step_url=view_name)
		extra = {}
		try:
			extra = json.loads(current_workflow_step.extra)
		except ValueError as ex:
			print 'was no extra info for this workflow step'
			# if no extra information was specified for this step, catch this exception and ignore it
			pass
		sample_source_upload = False
		if 'sample_source_upload' in extra:
			sample_source_upload = True

		existing_files = []
		if sample_source_upload:
			uploaded_files = project.datasource_set.all() # gets the files with this as their project
			sample_datasource_objs = []
			for f in uploaded_files:
				try:
					ds = f.sampledatasource
					if ds.sample:
						samplename = ds.sample.name
					else:
						samplename = None
					existing_files.append(FileDisplay(samplename, f.pk, f.filepath))
				except ObjectDoesNotExist as ex:
					print 'object was a regular DataSource, NOT a SampleDataSource. Skip'
					pass
		else:
			uploaded_files = project.datasource_set.all() # gets the files with this as their project
			for f in uploaded_files:
				try:
					# if the uploaded file was NOT associated with a sample, it will throw an exception
					ds = f.sampledatasource
				except ObjectDoesNotExist as ex:
					# catch the exception, which means we have a sample-agnostic file
					existing_files.append(FileDisplay(None, f.pk, f.filepath))

		instructions = current_workflow_step.instructions
		previous_url, next_url = helpers.get_bearings(project)
					
		context = {'project_name': project.name, \
				'existing_files':existing_files, \
				'project_pk': project_pk, \
				'instructions':instructions, \
				'previous_page_url':previous_url, \
                                'next_page_url':next_url, \
				'sample_source_upload':sample_source_upload, \
				'title_text': current_workflow_step.title_text \
			}
		return render(request, 'analysis_portal/upload_page.html', context)
	else:        
		return HttpResponseBadRequest('')
	

@login_required
def change_project_name(request, project_pk):
	"""
	Called (via ajax) to change the name of the project
	"""
	project = helpers.check_ownership(project_pk, request.user)
	if project is not None:
		project.name = request.POST.get('new_name')
		project.save()
		return HttpResponse("")
	else:
		return HttpResponseBadRequest('')


@login_required
def add_new_file(request, project_pk):
    project = helpers.check_ownership(project_pk, request.user)
    if project is not None:
        print request.POST
        newfile = request.POST.get('filename')
        is_sample_source_upload = request.POST.get('sample_source_upload')
        if is_sample_source_upload.lower() == 'true':
            is_sample_source_upload = True
        else:
            is_sample_source_upload = False
            
        print 'is_sample_source_upload: %s' % is_sample_source_upload
        newfile = os.path.join(settings.UPLOAD_PREFIX, newfile)
        try:
            return helpers.add_datasource_to_database(project, newfile, is_sample_source_upload)
        except helpers.UndeterminedFiletypeException as ex:
            return HttpResponseBadRequest(ex.message)
    else:
		return HttpResponseBadRequest('')


@login_required
def delete_file(request, project_pk):
	"""
	Called (via ajax) when removing a file.  Note that this does not remove the file from google storage bucket.
	It only removes the record of it from our database.
	TODO: change that-- remove from google storage as well.
	"""
	project = helpers.check_ownership(project_pk, request.user)
	if project is not None:
		file_to_rm = request.POST.get('filename')
		file_to_rm = os.path.join(settings.UPLOAD_PREFIX, file_to_rm)
		instance = DataSource.objects.get(filepath=file_to_rm, project=project)	
		instance.delete()
		return HttpResponse('')
	else:
		return HttpResponseBadRequest('')
		

@login_required
def annotate_files_and_samples(request, project_pk):
	"""
	Populates the annotation page
	TODO: infer samples from filenames
	"""
	project = helpers.check_ownership(project_pk, request.user)
	if project is not None:
		zero_uploaded_files = True
		# gets all files associated with project.  Some may be sample-specific, some not
		uploaded_files = project.datasource_set.all()

		# filter down to sample-specific files
		sample_datasource_objs = []
		for f in uploaded_files:
			try:
				ds = f.sampledatasource
				sample_datasource_objs.append(f)
			except ObjectDoesNotExist as ex:
				print 'object was a regular DataSource, NOT a SampleDataSource.  Skip'

		if len(sample_datasource_objs) > 0:
		    zero_uploaded_files = False
		existing_samples = project.sample_set.all() # any samples that were already defined

		unassigned_files = []
		assigned_files = {x.name:[] for x in existing_samples}
		for f in sample_datasource_objs:
			fds = f.sampledatasource
			fdisplay = FileDisplay('', f.pk, f.filepath)
			if fds.sample in existing_samples:
				assigned_files[fds.sample.name].append(fdisplay)
			else:
				unassigned_files.append(fdisplay)
		previous_url, next_url = helpers.get_bearings(project)
		context = {'project_name': project.name, \
				'unassigned_files':unassigned_files, \
				'assigned_files': assigned_files, \
				'project_pk': project_pk, \
				'no_uploaded_files':zero_uploaded_files,
                                'previous_page_url':previous_url, \
                                'next_page_url':next_url}
		return render(request, 'analysis_portal/annotate.html', context)
	else:
		return HttpResponseBadRequest('')
				
		
@login_required
def create_sample(request, project_pk):
	"""
	Called (via ajax) when creating a new sample in the UI
	"""
	project = helpers.check_ownership(project_pk, request.user)
	if project is not None:
		name = request.POST.get('name')
		metadata = request.POST.get('metadata')
		try:
			s = Sample(name=name, metadata=metadata, project=project)
			s.save()
		except:
			return HttpResponseBadRequest('')
		return HttpResponse('');
	else:
		return HttpResponseBadRequest('')


@login_required
def rm_sample(request, project_pk):
	"""
	Removes a sample. 
	As part of this, resets the 'sample' attribute of the DataSource.
	So, keeps the datasource, but just removes that file's association with the deleted sample
	"""
	project = helpers.check_ownership(project_pk, request.user)
	if project is not None:
		name = request.POST.get('samplename')
		s = Sample.objects.get(name=name, project=project)

		# get all the data sources assigned to this sample and set their sample attribute to be None
		ds_set = s.sampledatasource_set.all()
		for ds in ds_set:
			ds.sample = None
			ds.save()
		# finally, delete the Sample object
		s.delete()
		return HttpResponse('')
	else:
		return HttpResponseBadRequest('')


@login_required
def map_files_to_samples(request, project_pk):
	project = helpers.check_ownership(project_pk, request.user)
	if project is not None:
		j = json.loads(request.POST.get('mapping'))
		print 'received %s' % j
		all_samples = project.sample_set.all()
		print all_samples
		for sample, files in j.items():
			print 'try sample %s, files: %s' % (sample, files)
			sample_obj = project.sample_set.get(name=sample)
			print sample_obj
			for f in files:
				f = os.path.join(settings.UPLOAD_PREFIX,f)
				ds = SampleDataSource.objects.get(filepath=f, project=project)
				ds.sample = sample_obj
				ds.save()
		return HttpResponse('')
	else:
		return HttpResponseBadRequest('')


@login_required
def summary(request, project_pk):
	"""
	Summarizes the project prior to performing the analysis
	"""
	project = helpers.check_ownership(project_pk, request.user)
	if project is not None:
		full_mapping = {}
		all_samples = project.sample_set.all()
		for s in all_samples:
			data_sources = s.sampledatasource_set.all()	
			full_mapping[s] = ', '.join([os.path.basename(x.filepath) for x in data_sources])
		previous_url, next_url = helpers.get_bearings(project)
		context = {'mapping':full_mapping, \
				'project_pk':project.pk, \
				'project_name':project.name,\
                                'previous_page_url':previous_url, \
                                'next_page_url':next_url}
		return render(request, 'analysis_portal/summary.html', context)
	else:
		return HttpResponseBadRequest('')


@login_required
def kickoff(request, project_pk):
	"""
	Starts the analysis
	TODO: abstract this for ease
	"""
	project = helpers.check_ownership(project_pk, request.user)
	if project is not None:
		project_samples = project.sample_set.all()
		if len(project_samples) <= project.max_sample_number:
			pk = project.pk
			if project.service.name == 'rnaseq':
				rnaseq_process.start_analysis(pk)
				project.in_progress = True
				project.start_time = datetime.datetime.now()
				project.status_message = 'Performing alignments'
				project.next_action_text = 'Processing...'
				project.next_action_url = reverse('in_progress_view', kwargs={'project_pk':pk})
				project.save()
			elif project.service.name == 'variant_calling_from_bam':
				variant_process_submission_from_bam.start_analysis(pk)
			elif project.service.name == 'variant_calling_from_fastq':
				variant_process_submission_from_fastq.start_analysis(pk)
			elif project.service.name == 'pooled_crispr':
				pooled_crispr_process.start_analysis(pk)
				project.in_progress = True
				project.start_time = datetime.datetime.now()
				project.status_message = 'Performing quantification'
				project.next_action_text = 'Processing...'
				project.next_action_url = ''
				project.save()
			elif project.service.name == 'circ_rna':
				circ_rna_process.start_analysis(pk)
				project.in_progress = True
				project.start_time = datetime.datetime.now()
				project.status_message = 'Performing quantification'
				project.next_action_text = 'Processing...'
				project.next_action_url = ''
				project.save()

			else:
				print 'Could not figure out project type'
			return redirect('analysis_home_view')
		else:
			# had too many samples
			return redirect('problem_view', project_pk = project_pk)
	else:
		return HttpResponseBadRequest('')
