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
from client_setup.models import Project, Sample
from download.models import Resource

from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist

import config_parser

#from . import tasks

CALLBACK_URL = 'analysis/notify/'

def launch(project_pk, config_params):

    compute = googleapiclient.discovery.build('compute', 'v1')
    
    # note that project was already confirmed for ownership previously.  No need to check here.
    project = Project.objects.get(pk=project_pk)

    bucket_name = project.bucket
    
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

    # the sum of the uploads (in gb).  We need to be able to load the fastq and create BAM files, etc. so we need
    # to ensure we have sufficient disk space on the new VM.  
    total_upload_size = pd.np.sum(filesizes)/1e9
    necessary_size = float(config_params['size_buffer_factor'])*total_upload_size 
    if necessary_size > config_params['min_disk_size']:
        disk_size = int(necessary_size)
    else:
        disk_size = int(config_params['min_disk_size'])

    # the output bucket where results go
    result_bucket_name = os.path.join(bucket_name, config_params['output_bucket'])

    # get the mapping of samples to data sources:
    sample_string = ''
    fastq_string = ''
    all_samples = project.sample_set.all()
    for ds in datasources:
        try:
            sds = ds.sampledatasource
            if sds.sample in all_samples:      
                sample_string += ' ' + sds.sample.name
                fq_file = settings.GOOGLE_BUCKET_PREFIX + os.path.join(bucket_name, sds.filepath) 
                fastq_string += ' ' + fq_file
        except ObjectDoesNotExist as ex:
            print 'object was a regular DataSource, NOT a SampleDataSource.'
            library = settings.GOOGLE_BUCKET_PREFIX + os.path.join(bucket_name, ds.filepath)

    merged_counts_filename = config_params['merged_counts_filename']
    result_bucket_name = settings.GOOGLE_BUCKET_PREFIX + result_bucket_name
    email_utils = settings.GOOGLE_BUCKET_PREFIX + os.path.join(settings.STARTUP_SCRIPT_BUCKET, config_params['email_utils'])
    email_credentials = settings.GMAIL_CREDENTIALS_CLOUD
    scripts_bucket = settings.GOOGLE_BUCKET_PREFIX + os.path.join(settings.STARTUP_SCRIPT_BUCKET, config_params['scripts_dir'])
    cccb_project_pk = project.pk
    callback_url = '%s/%s' % (settings.HOST, CALLBACK_URL)
    startup_script_url = settings.GOOGLE_BUCKET_PREFIX + os.path.join(settings.STARTUP_SCRIPT_BUCKET, config_params['scripts_dir'], config_params['startup_script'])
    notification_email_addresses = settings.CCCB_EMAIL_CSV
    token = settings.TOKEN
    enc_key = settings.ENCRYPTION_KEY
    instance_name = 'pooled-crispr-worker-%s' % datetime.datetime.now().strftime('%m%d%y%H%M%S')

    google_project = settings.GOOGLE_PROJECT
    source_disk_image = config_params['image_name']
    machine_type = "zones/%s/machineTypes/%s" % (settings.GOOGLE_DEFAULT_ZONE, config_params['machine_type']) 

    config = {
        'name': instance_name,
        'machineType': machine_type,

        # Specify the boot disk and the image to use as a source.
        'disks': [
            {
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': source_disk_image,
                    'diskSizeGb': disk_size,
                }
            }
        ],

        # Specify a network interface with NAT to access the public
        # internet.
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [
                {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
            ]
        }],

        # Allow the instance to access cloud storage and logging.
        'serviceAccounts': [{
            'email': 'default',
            'scopes': [
                'https://www.googleapis.com/auth/compute',
                'https://www.googleapis.com/auth/devstorage.read_write',
                'https://www.googleapis.com/auth/logging.write'
            ]
        }],
 
        'metadata': {
            'items': [{
                # Startup script is automatically executed by the
                # instance upon startup.
                'key': 'startup-script-url',
                'value': startup_script_url
            },
            {
              'key':'result_bucket',
              'value': result_bucket_name
            },
            {
              'key':'google_project',
              'value': google_project
            },
            {
              'key':'google_zone',
              'value': settings.GOOGLE_DEFAULT_ZONE
            },
            {
              'key':'project_pk',
              'value': cccb_project_pk
            },
            {
                'key':'callback_url',
                'value': callback_url
            },
            {
              'key':'email_utils',
              'value': email_utils
            },
            {
              'key':'email_credentials',
              'value': email_credentials
            },
            {
              'key':'scripts-directory',
              'value': scripts_bucket
            },
            {
              'key':'notification_email_addresses',
              'value':notification_email_addresses
            },
            {
              'key':'token',
              'value':token
            },    
            {
              'key':'enc_key',
              'value':enc_key
            },
            {
              'key':'library-file',
              'value': library
            },
            {
              'key':'fastq-files',
              'value': fastq_string
            },
            {
              'key':'sample-names',
              'value': sample_string
            },
            {
              'key':'merged-counts-file',
              'value': merged_counts_filename
            },

          ]
        }
    }

    return compute.instances().insert(
        project=google_project,
        zone=settings.GOOGLE_DEFAULT_ZONE,
        body=config).execute()


def start_analysis(project_pk):
    config_params = config_parser.parse_config()
    launch(project_pk, config_params)
