import googleapiclient.discovery
from google.cloud import storage
import os
import sys
import glob
import re
import datetime

import pandas as pd

sys.path.append(os.path.abspath('..'))
import email_utils
from client_setup.models import Project, Sample
from cccb_portal.config_parser import parse_config as config_parser
from analysis_portal import helpers
from django.conf import settings

from celery.decorators import task

from . import plots

def get_files(all_cloud_files, local_dir, is_paired=True):
	"""
	Download the files locally
	"""
	if is_paired:
		patterns = ['glmReports/.*__circJuncProbs.txt', 'reports/.*_report.txt', 'ids/.*_output.txt']
		files_to_download = []
		for p in patterns:
			files_to_download.extend([x for x in all_cloud_files if re.match(p,'/'.join(x.name.split('/')[-2:]))])
	else:
		print 'Single end case'
		files_to_download = []
	for f in files_to_download:
		fname = os.path.basename(f.name)
		local_file = os.path.join(local_dir, fname)
		print 'Download %s to %s' % (f.name, local_file)
		f.download_to_filename(local_file)

def concatenate_circ_junction_reports(samples, local_dir, outfile, is_paired):
	overall_df = pd.DataFrame()
	for s in samples:
		prob_files = glob.glob(os.path.join(local_dir, '%s*__circJuncProbs.txt' % s.name))
		if len(prob_files) == 1:
			temp_df = pd.read_table(prob_files[0], index_col=0)
			temp_df = temp_df[['numReads', 'junction_cdf.x',]]
			temp_df.columns = ['numReads_%s' % s.name, 'junctionCDF_%s' % s.name]
			overall_df = pd.concat([overall_df, temp_df], axis=1)
		else:
			print 'More than one file matched!'
			raise Exception('Error when concatenating junction reports')
	overall_df.to_csv(outfile, sep='\t', index_label='junction_id')
	return overall_df


def make_figures(sample, concatenated_prob_df, gtf_filepath, output_dir, count_threshold = 10, cdf_threshold = 0.9):
	reads_files = glob.glob(os.path.join(output_dir, os.pardir, '%s*__output.txt' % sample.name))
	if len(reads_files) == 1:
		reads_file = reads_files[0]
	else:
		raise Exception('More than one reads file found for sample %s' % sample.name)

	df = concatenated_prob_df.ix[ \
		(concatenated_prob_df['numReads_%s' % sample.name] > count_threshold) \
		& \
		(concatenated_prob_df['junctionCDF_%s' % sample.name] > cdf_threshold) \
	]
	junctions = df.index.values
	plots.plot_circ_rna(junctions, reads_file, gtf_filepath, output_dir)


def get_gtf(storage_client, project, knife_resource_bucket):
	reference_genome = project.reference_organism.reference_genome
	bucket = storage_client.get_bucket(knife_resource_bucket)
	all_contents = bucket.list_blobs()

@task(name='finish_circ_rna_process')
def finish_circ_rna_process(project_pk):
	print 'Do some wrap-up of circRNA pipeline'

	project = Project.objects.get(pk=project_pk)

	config_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.cfg')
	config_params = config_parser(config_file)

	# Look into the bucket and pre-fetch the available objects
	storage_client = storage.Client()
	bucket_name = project.bucket
	bucket = storage_client.get_bucket(bucket_name)
	all_contents = bucket.list_blobs()
	all_contents = [x for x in all_contents] # turn the original iterator into a list

	local_dir = os.path.join(settings.TEMP_DIR, bucket.name)
	result_dir = os.path.join(local_dir, 'results')
	try:
		os.makedirs(result_dir)
	except OSError as ex:
		if ex.errno == 17:
			pass
		else:
			print ex.message
			raise ex 

	is_paired = get_paired_or_single_status(project_pk)
	all_samples = project.sample_set.all()

	# download the files to work on:
	get_files(all_contents, local_dir, is_paired)

	# download the proper GTF file for this project:
	gtf_filepath = get_gtf(project)

	concatenated_prob_file = os.path.join(result_dir, config_params['concatenated_probability_file'])
	concatenated_df = concatenate_circ_junction_reports(all_samples, local_dir, concatenated_prob_file, is_paired)

	count_threshold = int(config_params['count_threshold'])
	cdf_threshold = float(config_params['cdf_threshold'])
	for s in all_samples:
		sample_dir = os.path.join(result_dir, s.name)
		try:
			os.mkdir(sample_dir)
		except OSError as ex:
			if ex.errno == 17:
				pass
			else:
				print ex.message
				raise ex 
		make_figures(s, concatenated_df, gtf_filepath, output_dir, count_threshold, cdf_threshold)



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
				'value': param_dict['docker_image']
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
		{
			'key':'knife_resource_bucket',
			'value': param_dict['knife_resource_bucket']
		},
          ]
        }
    }

    return compute.instances().insert(
        project=google_project,
        zone=settings.GOOGLE_DEFAULT_ZONE,
        body=config).execute()
