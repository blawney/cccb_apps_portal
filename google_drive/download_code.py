import googleapiclient.discovery
import os
import glob
import json
from ConfigParser import SafeConfigParser
import sys
import datetime
import re
import subprocess

sys.path.append(os.path.abspath('..'))
import email_utils


from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist

CONFIG_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.cfg')

def parse_config():
    with open(CONFIG_FILE) as cfg_handle:
        parser = SafeConfigParser()
        parser.readfp(cfg_handle)
        return parser.defaults()

def transfer_files(project, transfer_json_str):
    """
    project is a Project object
    transfer_json_str is a JSON string with file ID mapping to file name
    """
    params = parse_config()
    owner = project.owner
    try:
        credentials_obj = DriveUserCredentials.objects.get(owner=owner)
        params['oauth2_credentials'] = credentials_obj.json_credentials
    except ObjectDoesNotExist as ex:
        #TODO issue some error-- this is a very unlikely exception
        pass
    params['user_email'] = owner.email
    params['project_pk'] = project.pk
    params['bucket_name'] = project.bucket
    params['transfer_json_str'] = transfer_json_str
    compute_client = googleapiclient.discovery.build('compute', 'v1')
    launch_custom_instance(compute_client, params)

def launch_custom_instance(compute, config_params):

    now = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    instance_name = '%s-drive-transfer' % now

    source_disk_image = 'projects/%s/global/images/%s' % (config_params['google_project'], config_params['image_name'])
    disk_size_in_gb = config_params['disk_size_in_db']
    machine_type = "zones/%s/machineTypes/%s" % (zone, config_params['machine_type'])
    startup_script_url = config_params['gs_prefix'] + os.path.join(config_params['startup_bucket'], config_params['startup_script']) 
    result_bucket_name = config_params['bucket_name']
    email_utils = config_params['gs_prefix'] + os.path.join(config_params['startup_bucket'], config_params['email_utils'])
    email_credentials = config_params['gs_prefix'] + os.path.join(config_params['startup_bucket'], config_params['email_credentials'])

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
                     "diskSizeGb": disk_size_in_gb,
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
                'https://www.googleapis.com/auth/devstorage.full_control',
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
              'key':'upload_folder', 
              'value':config_params['upload_folder']
            },
            {
              'key':'google_project',
              'value': config_params['google_project']
            },
            {
              'key':'google_zone',
              'value': config_params['default_zone']
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
              'key':'notification_email_addresses',
              'value':notification_email_addresses
            },
            {
              'key':'oauth2_credentials',
              'value':config_params['oauth2_credentials']
            },
            {
              'key':'transfer_json_str',
              'value':config_params['transfer_json_str']
            },
          ]
        }
    }
    return compute.instances().insert(
        project=google_project,
        zone=zone,
        body=config).execute()
