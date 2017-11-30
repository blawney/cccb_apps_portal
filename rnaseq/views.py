# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import os
import re
from ConfigParser import SafeConfigParser
import datetime

from django.shortcuts import render
from django.conf import settings
from google.cloud import storage
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, SuspiciousOperation

from django.http import HttpResponse, HttpResponseBadRequest

from client_setup.models import Project

from . import tasks

CONFIG_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.cfg')
RAW_COUNT_PREFIX = 'raw_counts'
ANNOTATION_FILE = 'sample_annotations.tsv'
DGE_FOLDER = 'dge'
DESEQ_SCRIPT = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'dge_script.R')

def parse_config():
	with open(CONFIG_FILE) as cfg_handle:
		parser = SafeConfigParser()
		parser.readfp(cfg_handle)
		return parser.defaults()


def check_ownership(project_pk, user):
    """
    Checks the ownership of a requested project (addressed by its db primary key)
    Returns None if the project is not found or some other exception is thrown
    Since this is not called directly, we cannot return any httpresponses directly to the client
    """
    try:
        project_pk = int(project_pk)
        print 'about to query project'
        project = Project.objects.get(pk=project_pk)
        if project.owner == user:
            return project
        else:
            return None # if not the owner
    except ObjectDoesNotExist as ex:
        raise SuspiciousOperation
    except:
        return None # if exception when parsing the primary key (or non-existant pk requested)


class SampleDisplay(object):
	def __init__(self, pk, name):
		self.pk = pk
		self.name = name


@login_required
def dge_setup_view(request, project_pk):
	"""
	Page where user assigns groups to perform DGE
	"""
	project = check_ownership(project_pk, request.user)
	if project:
		all_samples = project.sample_set.all()
		sample_display_objects = [SampleDisplay(s.pk, s.name) for s in all_samples]
		print sample_display_objects
		return render(request, 'rnaseq/dge_page.html', {'sample_set': sample_display_objects, 'project_name':project.name, 'project_pk':project.pk})
	else:
		return HttpResponseBadRequest('')	

def convert_name(y):
	y = y.replace(' ', '_')
	return ''.join([x for x in y if ((x.isalnum()) | (x == '_') | (x == '-'))])


@login_required
def perform_dge(request, project_pk):

	params = parse_config()

	project = check_ownership(project_pk, request.user)
	if project:
		j = json.loads(request.POST.get('info'))
		contrast_name = j['contrast_name']
		group_to_samples = j['mapping']
		l2fc_threshold = j['l2fc_threshold']
		pval_threshold = j['pval_threshold']

		try:
			l2fc_threshold = float(l2fc_threshold)
			pval_threshold = float(pval_threshold)
			if l2fc_threshold < 0:
				raise Exception('log2FC < 0')
			if ((pval_threshold <= 0) | (pval_threshold > 1)):
				raise Exception('pval is not in proper range (0,1]')
		except:
			#TODO send email to CCCB- they got through with a garbage value
			pass

		# convert any spaces to underscore and remove any non alpha-numeric
		gts = {}
		for key in group_to_samples.keys():
			gts[convert_name(key)] = group_to_samples[key]
		contrast_name = convert_name(contrast_name)

		print contrast_name
		print gts

		# will need the bucket :
		storage_client = storage.Client()
		bucket_name = project.bucket
		bucket = storage_client.get_bucket(bucket_name)
		local_dir = os.path.join(settings.TEMP_DIR, '%s-%s' % (bucket.name, datetime.datetime.now().strftime('%H%M%S')) )
		try:
			os.makedirs(local_dir)
		except OSError as ex:
			if ex.errno == 17:
				pass
			else:
				print ex.message
				raise ex

		# check that the samples are accounted for in this project.
		all_samples_dict = {s.pk:s for s in project.sample_set.all()}
		annotation_file = os.path.join(local_dir, ANNOTATION_FILE)
		try:
			with open(annotation_file, 'w') as fout:
				fout.write('Sample_ID\tGroup\n')
				for key, sample_pk_list in gts.items():
					sample_obj_list = [all_samples_dict[int(i)] for i in sample_pk_list]
					for s in sample_obj_list:
						fout.write('%s\t%s\n' % (s.name, key))

		except:
			print 'Something went wrong'
			#TODO send email/error msg



		# now, pull one of the raw count files
		all_contents = bucket.list_blobs()
		all_contents = [x for x in all_contents] # turn the original iterator into a list
		cloud_dge_dir = os.path.join(params['output_bucket'], DGE_FOLDER)
		count_matrix_pattern = '%s/%s.*' % (cloud_dge_dir, RAW_COUNT_PREFIX)
		count_matrix_objs = [x for x in all_contents if re.match(count_matrix_pattern, x.name) is not None]

		# call DESeq2 script- call asynchronously using celery
		#output_files = []
		for cm in count_matrix_objs:
			local_cm_path = os.path.join(local_dir, os.path.basename(cm.name))
			cm.download_to_filename(local_cm_path)
			result_filepath = '%s.deseq.tsv' % contrast_name
			norm_counts_filepath = '%s.normalized_counts.tsv' % contrast_name
			#r_script_cmd = 'Rscript %s %s %s %s %s %s %s' % (DESEQ_SCRIPT, local_cm_path, annotation_file, gts.keys()[0], gts.keys()[1], result_filepath, norm_counts_filepath)
			r_script_cmd = 'Rscript %s %s %s %s %s %s %s %s' % (DESEQ_SCRIPT, local_dir, os.path.basename(local_cm_path), os.path.basename(annotation_file), result_filepath, norm_counts_filepath, l2fc_threshold, pval_threshold)

			print r_script_cmd
			tasks.deseq_call.delay(r_script_cmd, local_dir, cloud_dge_dir, os.path.basename(local_cm_path), os.path.basename(annotation_file), norm_counts_filepath, contrast_name, bucket_name, project_pk)
			#output_files.append(result_filepath)

		project.status_message = 'Performing differential expression analysis'
		project.in_progress = True
		project.save()

		return HttpResponse('')
	else:
		return HttpResponseBadRequest('')
