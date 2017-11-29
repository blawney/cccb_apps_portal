#! /srv/venv/bin/python

import os
import sys
import io
import urllib
import urllib2
import subprocess
import dropbox
import datetime
import logging
from Crypto.Cipher import DES
import base64
import requests
from apiclient.discovery import build

WORKING_DIR = '/workspace'
DEFAULT_TIMEOUT = 60
DEFAULT_CHUNK_SIZE = 100*1024*1024 # dropbox says <150MB per chunk
METADATA_REQUEST_URL = 'http://metadata/computeMetadata/v1/instance/attributes/%s'

class MissingParameterException(Exception):
        pass

class CopyException(Exception):
        pass

def create_logger():
	"""
	Creates a logfile
	"""
	timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
	logfile = os.path.join(WORKING_DIR, str(timestamp)+".dropbox_transfer.log")
	print 'Create logfile at %s' % logfile
	logging.basicConfig(filename=logfile, level=logging.INFO, format="%(asctime)s:%(levelname)s:%(message)s")
	return logfile


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


def get_parameters():
	'''
	Gets the necessary parameters for the alignment.
	Pulls from the instance metadata
	returns a dictionary 
	'''
	# these are params that should have been passed via the metadata field during instance launch
	EXPECTED_PARAMS = ['callback_url', 'master_pk', 'dropbox_token', 'source', 'token', 'enc_key', 'google_project', 'google_zone', 'email_utils', 'email_credentials', 'cccb_email_csv', 'transfer_pk', 'dropbox_destination_folderpath']
	logging.info('Get required parameters from instance metadata')
	params = dict(zip(EXPECTED_PARAMS, map(get_metadata_param, EXPECTED_PARAMS)))
	# for consistent reference later:
	params['working_dir'] = WORKING_DIR
	return params


def get_instance_name():
	logging.info('Getting instance name')
	# get the instance name.  returns a name like 'test-upload-instance.c.cccb-data-delivery.internal'
	url = 'http://metadata/computeMetadata/v1/instance/hostname'
	request = urllib2.Request(url)
	request.add_header('X-Google-Metadata-Request', 'True')
	response = urllib2.urlopen(request)
	result = response.read()
	return result.split('.')[0]

def kill_instance(params):
	logging.info('Killing instance since work is complete')
	instance_name = get_instance_name()
	compute = build('compute', 'v1')
	compute.instances().delete(project=params['google_project'], zone=params['google_zone'], instance=instance_name).execute()


def notify_master(params, error=False):
	logging.info('Notifying the master that this job has completed')
	d = {}
	token = params['token']
	obj=DES.new(params['enc_key'], DES.MODE_ECB)
	enc_token = obj.encrypt(token)
	b64_str = base64.encodestring(enc_token)
	d['token'] = b64_str
	master_pk = params['master_pk']
	transfer_pk = params['transfer_pk']
	d['masterPK'] = master_pk
	d['transferPK'] = transfer_pk
	d['error'] = 1 if error else 0 # False for default
	base_url = params['callback_url']
	data = urllib.urlencode(d)
	request = urllib2.Request(base_url, {'Content-Type': 'application/json'})
	response = urllib2.urlopen(request, data=data)
	logging.info('response: %s' % response.read())

def gs_copy_file(src, dest):
	cp_cmd = 'gsutil cp gs://%s %s' % (src, dest)
	logging.info('Attempting to copy with command: %s' % cp_cmd)
	process = subprocess.Popen(cp_cmd, shell=True, stderr = subprocess.STDOUT, stdout = subprocess.PIPE)
	stdout, stderr = process.communicate()
	if process.returncode != 0:
		raise CopyException('Could not execute the following copy command: %s' % cp_cmd)

def download_to_disk(params):
	src = params['source']
	dest = params['working_dir'] + '/'
	gs_copy_file(src, dest)

def send_to_dropbox(params):
	token = params['dropbox_token']
	client = dropbox.dropbox.Dropbox(token, timeout=DEFAULT_TIMEOUT)
	filename = os.path.basename(params['source'])
	filepath = os.path.join(params['working_dir'], filename)
	file_size = os.path.getsize(filepath)

	stream = open(filepath)
	path_in_dropbox = '%s/%s' % (params['dropbox_destination_folderpath'], filename)
	if file_size <= DEFAULT_CHUNK_SIZE:
		client.files_upload(stream.read(), path_in_dropbox)
	else:
		i = 1
		session_start_result = client.files_upload_session_start(stream.read(DEFAULT_CHUNK_SIZE))
		cursor=dropbox.files.UploadSessionCursor(session_start_result.session_id, offset=stream.tell())
		commit=dropbox.files.CommitInfo(path=path_in_dropbox)
		while stream.tell() < file_size:
			logging.info('Sending chunk %s' % i)
			try:
				if (file_size-stream.tell()) <= DEFAULT_CHUNK_SIZE:
					logging.info('Finishing transfer and committing')
					client.files_upload_session_finish(stream.read(DEFAULT_CHUNK_SIZE), cursor, commit)
				else:
					logging.info('About to send chunk')
					logging.info('Prior to chunk transfer, cursor=%d, stream=%d' % (cursor.offset, stream.tell()))
					client.files_upload_session_append_v2(stream.read(DEFAULT_CHUNK_SIZE), cursor)
					cursor.offset = stream.tell()
					logging.info('Done with sending chunk')
			except dropbox.exceptions.ApiError as ex:
				logging.error('Raised ApiError!')
				if ex.error.is_incorrect_offset():
					logging.error('The error raised was an offset error.  Correcting the cursor and stream offset')
					correct_offset = ex.error.get_incorrect_offset().correct_offset
					cursor.offset = correct_offset
					stream.seek(correct_offset)
				else:
					logging.error('API error was raised, but was not offset error')
					raise ex
			except requests.exceptions.ConnectionError as ex:
				logging.error('Caught a ConnectionError exception')
				# need to rewind the stream
				logging.info('At this point, cursor=%d, stream=%d' % (cursor.offset, stream.tell()))
				cursor_offset = cursor.offset
				stream.seek(cursor_offset)
				logging.info('After rewind, cursor=%d, stream=%d' % (cursor.offset, stream.tell()))
				notify_cccb_of_error(params, msg="<html><body>Caught a ConnectionError.  Check instance %s</body></html>" % get_instance_name())
				logging.info('Go try that chunk again')
			except requests.exceptions.RequestException as ex:
				logging.error('Caught an exception during chunk transfer')
				logging.info('Following FAILED chunk transfer, cursor=%d, stream=%d' % (cursor.offset, stream.tell()))
				raise ex
			i += 1
	stream.close()


def notify_cccb_of_error(params, msg=None):
	logging.info('notify cccb of error')
	gs_copy_file(params['email_utils'], '/%s' % params['email_utils'].split('/')[-1])
	gs_copy_file(params['email_credentials'], '/%s' % params['email_credentials'].split('/')[-1])
	import importlib
	sys.path.append('/')
	module_name = params['email_utils'].split('/')[-1][:-3]
	email_utils = importlib.import_module(module_name)
	logging.info('Done loading module, about to send email')
	instance_name = get_instance_name()
	if not msg:
		msg = """
		    <html>
		    <body>
		            There was a problem with the transfer to Dropbox.  Check instance %s
		    </body>
		    </html>
		""" % instance_name
	# note that the email has to be nested in a list
	email_utils.send_email(os.path.join('/', params['email_credentials'].split('/')[-1]), msg, params['cccb_email_csv'].split(','), '[CCCB] Error with Dropbox transfer')

if __name__ == '__main__':
	os.mkdir(WORKING_DIR)
	logfile = create_logger()
	try:
		params = get_parameters()
		params['logfile'] = logfile
		download_to_disk(params)
		send_to_dropbox(params)
		notify_master(params)
		kill_instance(params)
	except Exception as ex:
		logging.error('Caught some unexpected exception.')
		logging.error(str(type(ex)))
		logging.error(ex)
		notify_cccb_of_error(params)
		notify_master(params, error=True)

