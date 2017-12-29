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
from cccb_portal.config_parser import parse_config as config_parser

from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist


@task(name='finish_circ_rna_process')
def finish_circ_rna_process(project_pk):
	print 'Do some wrap-up of circRNA pipeline'


@task(name='launch_circ_rna_worker')
def launch_circ_rna_worker(param_dict):

    compute = googleapiclient.discovery.build('compute', 'v1')
    
    instance_name = 'circ-rna-worker-%s' % datetime.datetime.now().strftime('%m%d%y%H%M%S')

    google_project = settings.GOOGLE_PROJECT
    machine_type = "zones/%s/machineTypes/%s" % (settings.GOOGLE_DEFAULT_ZONE, param_dict['machine_type']) 

    config = {
        'name': instance_name,
        'machineType': machine_type,

        'labels':[{
                    'key':'ilab_id',
                    'value':param_dict['ilab_id']
                   }
                 ],
        # Specify the boot disk and the image to use as a source.
        'disks': [
            {
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': param_dict['image_name'],
                    'diskSizeGb': param_dict['disk_size'],
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
                'value': param_dict['startup_script_url']
            },
            {
              'key':'result_bucket',
              'value': param_dict['result_bucket']
            },
            {
              'key':'google_project',
              'value': settings.GOOGLE_PROJECT
            },
            {
              'key':'google_zone',
              'value': settings.GOOGLE_DEFAULT_ZONE
            },
            {
              'key':'project_pk',
              'value': param_dict['cccb_project_pk']
            },
            {
                'key':'callback_url',
                'value': param_dict['callback_url']
            },
            {
              'key':'scripts-directory',
              'value': param_dict['scripts_bucket']
            },
            {
              'key':'token',
              'value':param_dict['token']
            },    
            {
              'key':'enc_key',
              'value':param_dict['enc_key']
            },
			{
				'key': 'reference_genome',
				'value': param_dict['reference_genome']
			},
			{
				'key': 'sample_pk',
				'value': param_dict['sample_pk']
			},
			{
				'key': 'r1_fastq',
				'value': param_dict['r1_fastq']
			},
			{
				'key': 'r2_fastq',
				'value': param_dict['r2_fastq']
			},
			{
				'key': 'docker_image',
				'value': param_dict['docker_image]
			},
			{
				'key': 'service_account_credentials',
				'value': param_dict['service_account_credentials']
			},
			{
				'key': 'dataset_name',
				'value': param_dict['dataset_name']
			},
			{
				'key':'read_length_script',
				'value': param_dict['read_length_script']
			},
			{
				'key':'read_samples',
				'value': param_dict['read_samples']
			},
          ]
        }
    }

    return compute.instances().insert(
        project=google_project,
        zone=settings.GOOGLE_DEFAULT_ZONE,
        body=config).execute()
