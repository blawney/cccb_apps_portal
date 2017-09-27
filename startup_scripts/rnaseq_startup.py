#! /srv/venv/bin/python

import jinja2
import os
from ConfigParser import SafeConfigParser
import urllib
import urllib2
import sys
import glob
import subprocess
import logging
import datetime
import googleapiclient.discovery
from Crypto.Cipher import DES
import base64

COUNTFILE_EXTENSION = 'counts'
WORKING_DIR = '/workspace'
ALIGNMENT_DIR = os.path.join(WORKING_DIR, 'align')
METADATA_REQUEST_URL = 'http://metadata/computeMetadata/v1/instance/attributes/%s'
GS_PREFIX = 'gs://'


class IncorrectConfigurationException(Exception):
	pass


class MissingParameterException(Exception):
	pass


class AlignmentScriptException(Exception):
	pass


class CopyException(Exception):
	pass


def create_logger():
	"""
	Creates a logfile
	"""
	timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
	logfile = os.path.join(WORKING_DIR, str(timestamp)+".alignment.log")
	print 'Create logfile at %s' % logfile
	logging.basicConfig(filename=logfile, level=logging.INFO, format="%(asctime)s:%(levelname)s:%(message)s")
	return logfile

def gs_copy(src, dest, recursive=False):
	#TODO: add kwargs?
	CMD = 'gsutil cp %s %s %s'
	
	if not src.startswith(GS_PREFIX) and not dest.startswith(GS_PREFIX):
		print 'Neither source nor destination locations had the appropriate filestore prefix (%s)' % GS_PREFIX
		sys.exit(1)
	else:
		if recursive:
			cp_cmd = CMD % ('-r', src, dest)
		else:
			cp_cmd = CMD % ('', src, dest)
		logging.info('Attempting to copy with command: %s' % cp_cmd)
		process = subprocess.Popen(cp_cmd, shell=True, stderr = subprocess.STDOUT, stdout = subprocess.PIPE)
		stdout, stderr = process.communicate()
		if process.returncode != 0:
			raise CopyException('Could not execute the following copy command: %s' % cp_cmd)


def set_filename_meta(root):
	"""
	This sets the filenames so they are not prepended with path information.  By default, a file uploaded to gs://bucket/foo/bar.txt
	ends up downloading with the filename foo_bar.txt.  This function makes it simply bar.txt
	root is a path like gs://something on google storage
	"""
	set_meta_cmd = 'gsutil setmeta -h "Content-Disposition: attachment; filename=%s" gs://%s/%s'

	# get the files:
	p = subprocess.Popen('gsutil ls -r %s' % root, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	ls_stdout, ls_stderr = p.communicate()
	if p.returncode != 0:
		for l in ls_stdout.split('\n'):
			if len(l)>0 and not l.endswith(':'):
				# set some metadata so the download does NOT prepend junk onto the file name
				cmd = set_meta_cmd % (os.path.basename(l), l)
				logging.info('Issue system command for setting metadata on file: %s' % cmd)
				process = subprocess.Popen(cmd, shell = True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
				stdout, stderr = process.communicate()
				if process.returncode != 0:
					logging.error('There was an error while setting the metadata on the fastq with gsutil.  Check the logs.  STDERR was:%s' % stderr)



def get_metadata_param(param_key):
	'''
	Calls the metadata service to get the parameters passed to the current instance
	'''
	logging.info('Search for parameter %s in instance metadata' % param_key)
	request_url = METADATA_REQUEST_URL % param_key
	request = urllib2.Request(request_url)
	request.add_header('X-Google-Metadata-Request', 'True')
	try: 
		response = urllib2.urlopen(request) 
		data = response.read()
		return data
	except urllib2.HTTPError as ex:
		raise MissingParameterException('The parameter %s was not found on the metadata server' % param_key)
		

def parse_config_file(config_filepath, selected_section):
	'''
	Takes a path to a local configuration file and a string
	indicating which section to use for getting key-value pairs

	returns a dictionary
	'''
	logging.info('Parse config file at %s, looking for section %s' % (config_filepath, selected_section))
	parser = SafeConfigParser()
	with open(config_filepath) as cfg_handle:
		parser.readfp(cfg_handle)
		if selected_section in parser.sections():
			d = {}
			for opt in parser.options(selected_section):
				value = parser.get(selected_section, opt).strip()
				if len(value) > 0:
					d[opt] = value
		else:
			raise IncorrectConfigurationException('Could not find section named "%s" in your configuration file. ' % selected_section)
	return d


def get_parameters():
	'''
	Gets the necessary parameters for the alignment.
	Pulls from the instance metadata
	
	returns a dictionary 
	'''
	# these are params that should have been passed via the metadata field during instance launch
	EXPECTED_PARAMS = ['callback_url', 'result_bucket_name', 'sample_name', 'r1_fastq', 'r2_fastq', 'reference_genome', 'genome_config_path', 'align_script_template', 'google_project', 'google_zone', 'project_pk', 'sample_pk', 'email_utils', 'email_credentials', 'notification_email_addresses', 'token', 'enc_key']

	logging.info('Get required parameters from instance metadata')
	params = dict(zip(EXPECTED_PARAMS, map(get_metadata_param, EXPECTED_PARAMS)))

	# for consistent reference later:
	params['working_dir'] = WORKING_DIR
	params['alignment_dir'] = ALIGNMENT_DIR

	# assumption is that the master instance has found the various fastq files in their project directories.  
	if params['r2_fastq'] == '':
		params['is_paired'] = False 
	else: 
		params['is_paired'] = True

	local_config = os.path.join(params['working_dir'], 'genome_config.cfg')
	gs_copy(params['genome_config_path'], local_config)
	params.update(parse_config_file(local_config, params['reference_genome']))

	# these can be changed, but e just put dummy values for now
	params['flowcell_id'] = 'default_flowcell'
	params['lane'] = 'L001'
	params['barcode'] ='AAAAAA'

	return params


def pull_files(params):
	'''
	Gets files from storage
	'''
	# TODO: exception handling!

	dest = os.path.join(params['working_dir'], '%s')

	# Get the alignment script template:
	gs_copy(params['align_script_template'], dest % os.path.basename(params['align_script_template']))
	
	# reassign the template variable for easier reference later
	params['align_script_template'] = os.path.basename(params['align_script_template'])

	# Get the fastq files:
	gs_copy(params['r1_fastq'], dest % os.path.basename(params['r1_fastq'])) 
	params['r1_fastq'] = dest % os.path.basename(params['r1_fastq'])
	if params['is_paired']:
		gs_copy(params['r2_fastq'], dest % os.path.basename(params['r2_fastq']))
		params['r2_fastq'] = dest % os.path.basename(params['r2_fastq'])

	
def create_alignment_dir(params):
		# TODO: exception handling
		os.mkdir(params['alignment_dir'])


def create_script(params):
	'''
	Fills in the various parameters in the pre-formatted alignment script
	'''
	# when filling out the script, we have intentionally matched the keys in the params dict 
	# with the variables in the template script.  This way we don't do any extra conversions, etc.
	# to pass that to the templating engine
	logging.info('Creating alignment script from template...')
	env = jinja2.Environment(loader=jinja2.FileSystemLoader(params['working_dir']))
	template = env.get_template(params['align_script_template'])
	completed_template_path = os.path.join(params['alignment_dir'], params['sample_name'] + '.align.sh')
	params['completed_align_script'] = completed_template_path
	with open(completed_template_path, 'w') as fout:
		fout.write(template.render(params)) 
	# give executable privileges
	os.chmod(completed_template_path, 0775)
	

def launch_alignment(params):
    # set executable permissions
    # make the necessary system call
    # wait for completion
    logging.info('Start alignment at %s' % params['completed_align_script'])
    process = subprocess.Popen(params['completed_align_script'], shell=True, stderr = subprocess.STDOUT, stdout = subprocess.PIPE)
    stdout, stderr = process.communicate()
    logging.info('STDERR from alignment:\n %s' % stderr)
    logging.info('STDOUT from alignment:\n %s' % stdout)
    if process.returncode != 0:
        raise AlignmentScriptException('Exit code was non-zero for the alignment script: %s' % params['completed_align_script'])
        sys.exit(1)


def count_reads(params):
    bamfiles = glob.glob(os.path.join(params['alignment_dir'], params['sample_name'] + '*.bam'))
    FEATURE_COUNTS_PATH = '/apps/subread-1.5.2-Linux-x86_64/bin/featureCounts'
    GTF = params['gtf_filepath']
    base_cmd = '%s -t exon -g gene_name -a %s' % (FEATURE_COUNTS_PATH, GTF)

    if params['is_paired']:
        base_cmd += ' -p'

    for bam in bamfiles:
        logging.info('Count bamfile at %s' % bam)
        bam_name = os.path.basename(bam)[:-3] # strip off 'bam'
        outfile = os.path.join(WORKING_DIR, bam_name + COUNTFILE_EXTENSION)
        command = base_cmd + ' -o %s %s' % (outfile, bam)
        logging.info('Counting reads with: %s' % command)
        process = subprocess.Popen(command, shell = True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        stdout, stderr = process.communicate()
        logging.info('stdout from counting reads: %s' % stdout)
        logging.info('stderr from counting reads: %s' % stderr)
        if process.returncode != 0:
            logging.info('The return code from counting reads was not zero.')
            sys.exit(1)
    logging.info('Completed counting reads')


def push_files(params):
    '''
    Pushes files back to storage bucket 
    '''
    result_bucket_name = params['result_bucket_name'] # gs://<bucket>/rnaseq_results/ (already has the 'subdir' added on)
    result_bucket_name = os.path.join(result_bucket_name, params['sample_name'])
    gs_copy(params['alignment_dir'], result_bucket_name, recursive=True)

    # copy the count files
    countfiles = glob.glob(os.path.join(WORKING_DIR, '*' + COUNTFILE_EXTENSION))
    for cf in countfiles:
        gs_copy(cf, result_bucket_name)

    # copy the logfile
    gs_copy(params['logfile'], result_bucket_name)


def kill_instance(params):

    logging.info('Killing instance since work is complete')
    # get the instance name.  returns a name like 'test-upload-instance.c.cccb-data-delivery.internal'
    url = 'http://metadata/computeMetadata/v1/instance/hostname'
    request = urllib2.Request(url)
    request.add_header('X-Google-Metadata-Request', 'True')
    response = urllib2.urlopen(request)
    result = response.read()
    instance_name = result.split('.')[0]
    compute = googleapiclient.discovery.build('compute', 'v1')
    compute.instances().delete(project=params['google_project'], zone=params['google_zone'], instance=instance_name).execute()


def notify_master(params):
    logging.info('Notifying the master that this job has completed')
    d = {}
    token = params['token']
    obj=DES.new(params['enc_key'], DES.MODE_ECB)
    enc_token = obj.encrypt(token)
    b64_str = base64.encodestring(enc_token)
    d['token'] = b64_str
    d['projectPK'] = params['project_pk']
    d['samplePK'] = params['sample_pk']
    base_url = params['callback_url']

    data = urllib.urlencode(d)
    request = urllib2.Request(base_url, {'Content-Type': 'application/json'})
    response = urllib2.urlopen(request, data=data)
    logging.info('response: %s' % response.read())

def get_instance_name():
	logging.info('Getting instance name')
	# get the instance name.  returns a name like 'test-upload-instance.c.cccb-data-delivery.internal'
	url = 'http://metadata/computeMetadata/v1/instance/hostname'
	request = urllib2.Request(url)
	request.add_header('X-Google-Metadata-Request', 'True')
	response = urllib2.urlopen(request)
	result = response.read()
	return result.split('.')[0]


def notify_cccb_of_error(params):
	logging.info('notify cccb of error')
	gs_copy(params['email_utils'], '/%s' % params['email_utils'].split('/')[-1])
	gs_copy(params['email_credentials'], '/%s' % params['email_credentials'].split('/')[-1])
	import importlib
	sys.path.append('/')
	module_name = params['email_utils'].split('/')[-1][:-3]
	email_utils = importlib.import_module(module_name)
	logging.info('Done loading module, about to send email')
	instance_name = get_instance_name()
	msg = "<html><body>There was a problem with an alignment process.  Check instance %s</body></html>" % instance_name
	# note that the email has to be nested in a list
	email_utils.send_email(os.path.join('/', params['email_credentials'].split('/')[-1]), msg, [x.strip() for x in params['notification_email_addresses'].split(',')], '[CCCB] Error with rnaseq alignment worker')

if __name__ == '__main__':
	os.mkdir(WORKING_DIR)
	logfile = create_logger()
	try:
		params = get_parameters()
		params['logfile'] = logfile
		create_alignment_dir(params)
		pull_files(params)
		create_script(params)
		launch_alignment(params)
		count_reads(params)
		push_files(params)
		set_filename_meta(params['result_bucket_name'])
		notify_master(params)
		kill_instance(params)
	except Exception as ex:
		logging.error(str(type(ex)))
		logging.error(ex)
		logging.error('Exception caught: %s' % ex.message)

		notify_cccb_of_error(params)
		# TODO push the log file and kill this instance so we do not waste money
		#gs_copy(params['logfile'], params['result_bucket_name'])
		#kill_instance(params)
