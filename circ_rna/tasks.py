import googleapiclient.discovery
from google.cloud import storage
import os
import sys
import shutil
import glob
import re
import datetime
import subprocess 

import pandas as pd

sys.path.append(os.path.abspath('..'))
import email_utils
from client_setup.models import Project, Sample
from download.models import Resource
from cccb_portal.config_parser import parse_config as config_parser
from analysis_portal import helpers
from django.conf import settings

from celery.decorators import task

from . import plots

LINK_ROOT = settings.PUBLIC_STORAGE_ROOT + '%s/%s'


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
		if is_paired:
			prob_files = glob.glob(os.path.join(local_dir, '%s*__circJuncProbs.txt' % s.name))
			if len(prob_files) == 1:
				temp_df = pd.read_table(prob_files[0], index_col=0)
				temp_df = temp_df[['numReads', 'junction_cdf.x',]]
				temp_df.columns = ['numReads_%s' % s.name, 'junctionCDF_%s' % s.name]
				overall_df = pd.concat([overall_df, temp_df], axis=1)
			else:
				print 'More than one file matched!'
				raise Exception('Error when concatenating junction reports')
		else: # single end
			prob_files = glob.glob(os.path.join(local_dir, '%s*_report.txt' % s.name))
			if len(prob_files) == 1:
				temp_df = pd.read_table(prob_files[0], skiprows=1, index_col=0)
				temp_df = temp_df[['circ','pvalue']]
				temp_df.columns = ['numReads_%s' % s.name,'junctionCDF_%s' % s.name]
				non_reg_rows = temp_df.apply(lambda x: x.split('|')[-2] != 'reg', axis=1)
				temp_df = temp_df.ix[non_reg_rows]
				overall_df = pd.concat([overall_df, temp_df], axis=1)
			else:
				print 'More than one file matched for report in single-end circRNA run.'
				raise Exception('Error when concatenating the single-end junction files')
	overall_df.to_csv(outfile, sep='\t', index_label='junction_id')
	return overall_df


def make_figures(sample, concatenated_prob_df, gtf_filepath, output_dir, count_threshold = 10, cdf_threshold = 0.9):
	reads_files = glob.glob(os.path.join(output_dir, os.pardir, os.pardir, '%s*__output.txt' % sample.name))
	if len(reads_files) == 1:
		reads_file = os.path.realpath(reads_files[0])
	else:
		raise Exception('More than one reads file found for sample %s' % sample.name)

	df = concatenated_prob_df.ix[ \
		(concatenated_prob_df['numReads_%s' % sample.name] > count_threshold) \
		& \
		(concatenated_prob_df['junctionCDF_%s' % sample.name] > cdf_threshold) \
	]
	junctions = df.index.values
	plots.plot_circ_rna(junctions, reads_file, gtf_filepath, output_dir)


def get_gtf(storage_client, project, knife_resource_bucket, local_dir):
	reference_genome = project.reference_organism.reference_genome
	bucket = storage_client.get_bucket(knife_resource_bucket[len(settings.GOOGLE_BUCKET_PREFIX):])
	filename = '%s/%s_genes.gtf' % (reference_genome, reference_genome)
	print 'filename for gtf: %s' % filename
	local_path = os.path.join(local_dir, os.path.basename(filename))
	gtf_obj = bucket.get_blob(filename)
	gtf_obj.download_to_filename(local_path)
	return local_path
	
def write_completion_message(project):
    message_html = """\
    <html>
      <head></head>
      <body>
          <p>
            Your circRNA analysis (%s) is complete!  Log-in to the CCCB application site to view and download your results.
          </p>
      </body>
    </html>
    """ % project.name
    return message_html

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

	is_paired = helpers.get_paired_or_single_status(project_pk)
	all_samples = project.sample_set.all()

	# download the files to work on:
	get_files(all_contents, local_dir, is_paired)

	# download the proper GTF file for this project:
	gtf_filepath = get_gtf(storage_client, project, config_params['knife_resource_bucket'], local_dir)

	concatenated_prob_file = os.path.join(result_dir, config_params['concatenated_probability_file'])
	concatenated_df = concatenate_circ_junction_reports(all_samples, local_dir, concatenated_prob_file, is_paired)

	# upload the concatenated file:
	destination = os.path.join(config_params['output_bucket'], os.path.basename(concatenated_prob_file))
	cpf_blob = bucket.blob(destination)
	cpf_blob.upload_from_filename(concatenated_prob_file)
	acl = cpf_blob.acl
	entity = acl.user(project.owner.email)
	entity.grant_read()
	acl.save()

	public_link = LINK_ROOT % (bucket.name, cpf_blob.name)
	r = Resource(project=project, basename = os.path.basename(concatenated_prob_file), public_link = public_link, resource_type = 'circRNA quantification')
	r.save()

	# make directories for each sample to hold figures:
	count_threshold = int(config_params['count_threshold'])
	cdf_threshold = float(config_params['cdf_threshold'])
	all_sample_dirs = []
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
		make_figures(s, concatenated_df, gtf_filepath, sample_dir, count_threshold, cdf_threshold)
		all_sample_dirs.append(sample_dir)

	# zip up the figures:
	zipfile = os.path.join(local_dir, 'circ_rna_figures.zip') 
	zip_cmd = 'zip -r %s %s' % (zipfile, ' '.join(all_sample_dirs))
	print 'zip up using command: %s' % zip_cmd
	p = subprocess.Popen(zip_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	stdout, sterr = p.communicate()
	if p.returncode != 0:
		#TODO: send email to cccb?  Shouldn't happen and not a user error.
		pass

	# upload the archive and give it permissions:
	destination = os.path.join(config_params['output_bucket'], os.path.basename(zipfile))
	zip_blob = bucket.blob(destination)
	zip_blob.upload_from_filename(zipfile)
	acl = zip_blob.acl
	entity = acl.user(project.owner.email)
	entity.grant_read()
	acl.save()

	# change the metadata so the download does not append the path 
	set_meta_cmd = '%s setmeta -h "Content-Disposition: attachment; filename=%s" gs://%s/%s' % (settings.GSUTIL_PATH, os.path.basename(zipfile), bucket_name, destination)
	print 'Issue metadata command: %s' % set_meta_cmd
	process = subprocess.Popen(set_meta_cmd, shell = True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
	stdout, stderr = process.communicate()
	if process.returncode != 0:
		print 'There was an error while setting the metadata on the zipped archive with gsutil.  Check the logs.  STDERR was:%s' % stderr
		print 'STDOUT was %s' % stdout
		raise Exception('Error during gsutil upload module.')

	shutil.rmtree(local_dir)

	# register the zip archive with the download app
	public_link = LINK_ROOT % (bucket.name, zip_blob.name)
	r = Resource(project=project, basename = os.path.basename(zipfile), public_link = public_link, resource_type = 'Figures')
	r.save()

	# notify the client
	# the second arg is supposedd to be a list of emails
	print 'send notification email'
	message_html = write_completion_message(project)
	email_utils.send_email(os.path.join(settings.BASE_DIR, settings.GMAIL_CREDENTIALS), message_html, [project.owner.email,], '[CCCB] Your circRNA analysis has completed')	

@task(name='launch_circ_rna_worker')
def launch_circ_rna_worker(param_dict):

    compute = googleapiclient.discovery.build('compute', 'v1')
    
    instance_name = 'circ-rna-worker-%s-%s' % (datetime.datetime.now().strftime('%m%d%y%H%M%S'), param_dict['worker_num'])
    print 'Launch worker with name %s' % instance_name
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
