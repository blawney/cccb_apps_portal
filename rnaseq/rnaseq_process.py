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

import config_parser
import plot_methods

from . import tasks

CALLBACK_URL = 'analysis/notify/'

def setup(project_pk, config_params):
    
    # note that project was already confirmed for ownership previously.  No need to check here.
    project = Project.objects.get(pk=project_pk)

    # get the reference genome
    reference_genome = project.reference_organism.reference_genome
    config_params['reference_genome'] = reference_genome

    bucket_name = project.bucket
    
    # get datasources from db:
    datasources = project.datasource_set.all()
    datasource_paths = [os.path.join(bucket_name, x.filepath) for x in datasources]
    datasource_paths = [settings.GOOGLE_BUCKET_PREFIX + x for x in datasource_paths]

    # check that those datasources exist in the actual bucket
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    all_contents = bucket.list_blobs()
    uploads = [x.name for x in all_contents if x.name.startswith(config_params['upload_folder'])]
    
    # compare-- it's ok if there were more files in the bucket
    bucket_set = set(uploads)
    datasource_set = set(datasource_paths)
    if len(datasource_set.difference(uploads)) > 0:
        # TODO raise exception
        pass

    # create the output bucket
    result_bucket_name = os.path.join(bucket_name, config_params['output_bucket'])
    #result_bucket = storage_client.create_bucket(result_bucket_name)

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
    return project, result_bucket_name, final_mapping


def get_internal_ip():
    url = 'http://metadata/computeMetadata/v1/instance/network-interfaces/0/ip'
    request = urllib2.Request(url)
    request.add_header('X-Google-Metadata-Request', 'True')
    response = urllib2.urlopen(request)
    result = response.read()
    return result


def launch_workers(compute, project, result_bucket_name, sample_mapping, config_params):
    """
    sample_mapping is a dict with a (int,str) tuple (sample PK, sample name) as the key, pointing at a list of DataSource objects
    """
    # first, check that they list of DataSource objects are all the same length:
    length_list = []
    for sample_tuple, ds_list in sample_mapping.items():
        length_list.append(len(ds_list))
    lengthset = set(length_list)
    if len(lengthset) != 1:
        # TODO not all paired or single- raise error
        pass

    input_bucket_name = project.bucket
    for sample_tuple, ds_list in sample_mapping.items():
        file_list = sorted([settings.GOOGLE_BUCKET_PREFIX + os.path.join(input_bucket_name, ds.filepath) for ds in ds_list])
        kwargs = {}
        kwargs['r1_fastq'] = file_list[0]
        kwargs['r2_fastq'] = ''
        # if paired
        if len(file_list) == 2:
            kwargs['r2_fastq'] = file_list[1]
        elif len(file_list) > 2:
            #TODO: something weird happened
            pass
        # now add the other params to the dictionary:
        kwargs['result_bucket_name'] = settings.GOOGLE_BUCKET_PREFIX + result_bucket_name
        kwargs['reference_genome'] = config_params['reference_genome']
        kwargs['email_utils'] = settings.GOOGLE_BUCKET_PREFIX + os.path.join(settings.STARTUP_SCRIPT_BUCKET, config_params['email_utils'])
        kwargs['email_credentials'] = settings.GMAIL_CREDENTIALS_CLOUD
        kwargs['sample_name'] = sample_tuple[1] 
        kwargs['genome_config_path'] = settings.GOOGLE_BUCKET_PREFIX + os.path.join(settings.STARTUP_SCRIPT_BUCKET, config_params['genome_config_file'])
        kwargs['align_script_template'] = settings.GOOGLE_BUCKET_PREFIX + os.path.join(settings.STARTUP_SCRIPT_BUCKET, config_params['align_script_template'])
        kwargs['project_pk'] = project.pk
        kwargs['ilab_id'] = project.ilab_id.lower()
        kwargs['sample_pk'] = sample_tuple[0]
        kwargs['callback_url'] = '%s/%s' % (settings.HOST, CALLBACK_URL)
        kwargs['startup_script'] = settings.GOOGLE_BUCKET_PREFIX + os.path.join(settings.STARTUP_SCRIPT_BUCKET, config_params['startup_script'])
        kwargs['notification_email_addresses'] = settings.CCCB_EMAIL_CSV
        kwargs['token'] = settings.TOKEN
        kwargs['enc_key'] = settings.ENCRYPTION_KEY
        instance_name = 'worker-%s-%s' % (sample_tuple[1].lower().replace('_','-'), datetime.datetime.now().strftime('%m%d%y%H%M%S'))
        launch_custom_instance(compute, settings.GOOGLE_PROJECT, settings.GOOGLE_DEFAULT_ZONE, instance_name, kwargs, config_params)


def launch_custom_instance(compute, google_project, zone, instance_name, kwargs, config_params):

    result_bucket_name = kwargs['result_bucket_name']
    sample_name = kwargs['sample_name']
    r1_fastq = kwargs['r1_fastq']
    r2_fastq = kwargs['r2_fastq']
    reference_genome = kwargs['reference_genome']
    genome_config_path = kwargs['genome_config_path']
    align_script_template = kwargs['align_script_template']
    startup_script_url = kwargs['startup_script']
    cccb_project_pk = kwargs['project_pk']
    sample_pk = kwargs['sample_pk']
    callback_url = kwargs['callback_url']
    email_utils = kwargs['email_utils']
    email_credentials = kwargs['email_credentials']
    notification_email_addresses = kwargs['notification_email_addresses']
    token = kwargs['token']
    enc_key = kwargs['enc_key']
    source_disk_image = config_params['image_name']
    machine_type = "zones/%s/machineTypes/%s" % (zone, config_params['machine_type']) 

    config = {
        'name': instance_name,
        'machineType': machine_type,

        'labels':[{
                    'key':'ilab_id',
                    'value':kwargs['ilab_id']
                   }
                 ],
        # Specify the boot disk and the image to use as a source.
        'disks': [
            {
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': source_disk_image,
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
              'key':'result_bucket_name',
              'value': result_bucket_name
            },
            {
              'key':'sample_name',
              'value': sample_name
            },
            {
              'key':'r1_fastq',
              'value': r1_fastq
            },
            {
              'key':'r2_fastq',
              'value': r2_fastq
            },
            {
              'key':'reference_genome',
              'value': reference_genome
            },
            {
              'key':'genome_config_path',
              'value': genome_config_path
            },
            {
              'key':'align_script_template',
              'value': align_script_template
            },
            {
              'key':'google_project',
              'value': google_project
            },
            {
              'key':'google_zone',
              'value': zone
            },
            {
              'key':'project_pk',
              'value': cccb_project_pk
            },
            {
              'key':'sample_pk',
              'value': sample_pk
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
              'key':'notification_email_addresses',
              'value':notification_email_addresses
            },
            {
              'key':'token',
              'value':token
            },            {
              'key':'enc_key',
              'value':enc_key
            }

          ]
        }
    }
    print 'x'*20
    print config
    print 'x'*20
    return compute.instances().insert(
        project=google_project,
        zone=zone,
        body=config).execute()


def start_analysis(project_pk):
    config_params = config_parser.parse_config()
    project, result_bucket_name, sample_mapping = setup(project_pk, config_params)
    print 'done with setup'
    compute = googleapiclient.discovery.build('compute', 'v1')
    launch_workers(compute, project, result_bucket_name, sample_mapping, config_params)


def handle(project, request):
    """
    This is not called by any urls, but rather the request object is forwarded on from a central "distributor" method
    project is a Project object/model
    """
    print 'handling project %s' % project
    sample_pk = int(request.POST.get('samplePK', '')) #exceptions can be caught in caller
    print 'sample_pk=%s' % sample_pk
    sample = Sample.objects.get(pk = sample_pk)
    print 'here?'*10
    sample.processed = True
    sample.save()

    print 'saved'
    # now check to see if everyone is done
    all_samples = project.sample_set.all()
    if all([s.processed for s in all_samples]):
        print 'All samples have completed!'
        project.in_progress = False
        project.paused_for_user_input = True
        project.completed = True
        project.status_message = 'Completed alignments'
        project.next_action_text = 'Perform differential expression'
        project.next_action_url = reverse('dge', kwargs={'project_pk':project.pk})
        project.has_downloads = True
        project.save()
        tasks.finish_alignment_work.delay(project.pk)
