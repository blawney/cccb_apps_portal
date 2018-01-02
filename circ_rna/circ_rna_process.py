from google.cloud import storage
import googleapiclient.discovery
import os
import shutil
import glob
import json
import urllib
import urllib2
import sys
import datetime
import re
import subprocess

import pandas as pd

sys.path.append(os.path.abspath('..'))
import email_utils
from cccb_portal.config_parser import parse_config as config_parser
from client_setup.models import Project, Sample
from download.models import Resource

from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist

from . import tasks

CALLBACK_URL = 'analysis/notify/'

def handle(project, request):

	sample_pk = int(request.POST.get('samplePK', ''))
	sample = Sample.objects.get(pk = sample_pk)
	has_error = bool(int(request.POST.get('has_error', '')))
	if has_error:
		# notify CCCB
		print 'Error with circRNA worker'
		email_utils.send_email(os.path.join(settings.BASE_DIR, settings.GMAIL_CREDENTIALS), \
				"There was a problem with the circRNA worker for sample %s" % sample.name, settings.CCCB_EMAIL_CSV, '[CCCB] Problem with circRNA worker')
	else:
		sample.processed = True
		sample.save()

	# now check to see if everyone is done
	all_samples = project.sample_set.all()
	if all([s.processed for s in all_samples]):
		project.in_progress = False
		project.paused_for_user_input = False
		project.completed = True
		project.status_message = 'Complete'
		project.next_action_text = '-'
		project.next_action_url = ''
		project.has_downloads = True
		project.save()
		tasks.finish_circ_rna_process.delay(project.pk)


def prepare(project_pk, config_params):

    project = Project.objects.get(pk=project_pk)

    bucket_name = project.bucket

    # get the reference genome string:
    reference_genome = project.reference_organism.reference_genome
    
    # get datasources from db:
    datasources = project.datasource_set.all()
    datasource_paths = [os.path.join(bucket_name, x.filepath) for x in datasources]
    datasource_paths = [settings.GOOGLE_BUCKET_PREFIX + x for x in datasource_paths]

    # check that those datasources exist in the actual bucket
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    all_contents = bucket.list_blobs()
    uploads = []
    filesizes = []
    for x in all_contents:
        if x.name.startswith(config_params['upload_folder']):
            uploads.append(x.name)
            filesizes.append(x.size)

    # compare-- it's ok if there were more files in the bucket
    bucket_set = set(uploads)
    datasource_set = set(datasource_paths)
    if len(datasource_set.difference(uploads)) > 0:
        # TODO raise exception
        pass

    # the output bucket where results go.  Full path (e.g. gs://bucket/foo/bar)
    result_bucket = settings.GOOGLE_BUCKET_PREFIX + os.path.join(bucket_name, config_params['output_bucket'])

    # get the mapping of samples to data sources:
    sample_mapping = {}
    all_samples = project.sample_set.all()
    for s in all_samples:
        sample_mapping[(s.pk, s.name)] = []
    for ds in datasources:
        try:
            ds = ds.sampledatasource
            if ds.sample in all_samples:
                sample_mapping[(ds.sample.pk, ds.sample.name)].append(ds)
        except ObjectDoesNotExist as ex:
            pass 

    # just in case, remove any empty samples:
    final_mapping = {}
    for key, vals in sample_mapping.items():
        if len(vals) > 0:
            final_mapping[key] = vals

    # args that each spawned VM will need:
    base_kwargs = {}
    base_kwargs['reference_genome'] = reference_genome
    base_kwargs['scripts_bucket'] = settings.GOOGLE_BUCKET_PREFIX + os.path.join(settings.STARTUP_SCRIPT_BUCKET, config_params['scripts_dir'])
    base_kwargs['token'] = settings.TOKEN
    base_kwargs['enc_key'] = settings.ENCRYPTION_KEY
    base_kwargs['cccb_project_pk'] = project.pk
    base_kwargs['ilab_id'] = project.ilab_id.lower()
    base_kwargs['callback_url'] = '%s/%s' % (settings.HOST, CALLBACK_URL)
    base_kwargs['startup_script_url'] = os.path.join(base_kwargs['scripts_bucket'], config_params['startup_script'])
    base_kwargs['machine_type'] = config_params['machine_type']
    base_kwargs['disk_size'] = config_params['disk_size']
    base_kwargs['image_name'] = config_params['image_name']
    base_kwargs['docker_image'] = config_params['docker_image']
    base_kwargs['service_account_credentials'] = settings.SERVICE_ACCOUNT_CREDENTIALS_CLOUD
    base_kwargs['dataset_name'] = re.sub('[\s-]+', '_', project.name)
    base_kwargs['read_length_script'] = os.path.join(base_kwargs['scripts_bucket'], config_params['read_length_script'])
    base_kwargs['read_samples'] = config_params['read_samples']
    base_kwargs['knife_resource_bucket'] = config_params['knife_resource_bucket']

    for sample_tuple, ds_list in final_mapping.items():
        file_list = sorted([settings.GOOGLE_BUCKET_PREFIX + os.path.join(bucket_name, ds.filepath) for ds in ds_list])
        kwargs = base_kwargs.copy()
        kwargs['sample_pk'] = sample_tuple[0]
        kwargs['result_bucket'] = os.path.join(result_bucket, sample_tuple[1])
        kwargs['r1_fastq'] = file_list[0]
        kwargs['r2_fastq'] = '-'
        # if paired
        if len(file_list) == 2:
            kwargs['r2_fastq'] = file_list[1]		
		
        tasks.launch_circ_rna_worker.delay(kwargs)


def start_analysis(project_pk):
    config_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.cfg')
    config_params = config_parser(config_file)
    prepare(project_pk, config_params)
