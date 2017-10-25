# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest
import json
import requests
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import time
import urllib
import sys
import base64
import os
from django.contrib.auth.decorators import login_required
from google.cloud import storage  
from client_setup.models import Project

import email_utils
import analysis_portal.helpers as helpers
from . import tasks

from celery import chord

from django.conf import settings

SIGNED_URL_EXPIRATION = datetime.timedelta(days=1)

@login_required
def sign_url(request, project_pk):
	try:
		project_pk = int(project_pk)
		project = Project.objects.get(pk=project_pk)
		if project.owner == request.user:
			bucket_name = project.bucket
			set_bucket_cors(bucket_name)
			file_name = request.POST.get('filename')
			file_type = request.POST.get('filetype')

			file_name = os.path.join(settings.UPLOAD_PREFIX, file_name)
			resource = '/%s/%s' % (bucket_name, file_name)
			signed_url_for_post = create_signed_post_rq(resource)
			d = {}
			d['signed_url'] = signed_url_for_post
			return HttpResponse(json.dumps(d), content_type='application/json')
	except:
		return HttpResponseBadRequest('')

def set_bucket_cors(bucket_name):
	storage_client = storage.Client()
	bucket = storage_client.get_bucket(bucket_name)
	d=[{'origin': [settings.HOST], 
		'responseHeader': ['Access-Control-Allow-Origin', 'Content-Type', 'Content-Range', 'Access-Control-Allow-Headers', 'x-goog-resumable', 'Range'], 
		 'method': ['GET', 'PUT', 'POST'], 'maxAgeSeconds':3600},]
	bucket.cors = d
	bucket.patch()

def create_signed_post_rq(gcs_resource_path):
	method = "POST"
	expiration = datetime.datetime.utcnow() + SIGNED_URL_EXPIRATION
	expiration = int(time.mktime(expiration.timetuple()))
	signature_string = "\n".join([
		        method,
		        "",  # content md5
		        "text/plain",  # content type
		        str(expiration),
			    'x-goog-resumable:start',
		        gcs_resource_path
		])

	creds = ServiceAccountCredentials.from_json_keyfile_name(settings.URL_SIGNER_CREDENTIALS)
	client_id = creds.service_account_email
	signature = base64.b64encode(creds.sign_blob(signature_string)[1])
	query_params = {
			"GoogleAccessId": client_id,
			"Expires": str(expiration),
			"Signature": signature,
	}
        return "{endpoint}{resource}?{querystring}".format(
                        endpoint=settings.STORAGE_API_URI,
                        resource=gcs_resource_path,
                        querystring=urllib.urlencode(query_params))


@login_required
def dropbox_transfer(request, project_pk):
	print 'in drbx'
	print project_pk
	HTML_BODY = '<html><body>The following files were not named correctly and did not transfer.  Please correct them and try again. <ul>%s</ul></body></html>'
	try:
		project_pk = int(project_pk)
		project = Project.objects.get(pk=project_pk)
		if project.owner == request.user:
			print request.POST
			is_sample_datasource_upload = request.POST.get('sample_source_upload')
			print is_sample_datasource_upload			
			file_links = request.POST.get('transfer_files')
			file_links = [x.strip() for x in file_links.split(',')]
			print file_links
			all_transfers = []
			misnamed_file_list = []
			err_func = tasks.on_chord_error.s()
			for i,f in enumerate(file_links):
				print 'try to transfer %s' % f
				file_name = f.split('/')[-1]
				try:
					helpers.determine_filetype(file_name)
					destination = os.path.join(project.bucket, settings.UPLOAD_PREFIX, file_name)
					destination = destination.replace(' ', '_')
					print 'make transfer with %s' % file_name
					all_transfers.append(tasks.dropbox_transfer_to_bucket.s(f, destination, project.pk, is_sample_datasource_upload))
				except helpers.UndeterminedFiletypeException as ex:
					print 'problem with %s' % file_name
					misnamed_file_list.append(file_name)
			if len(misnamed_file_list) > 0:
				print 'send a message- %s' % misnamed_file_list
				file_str = ''.join(['<li>%s</li>' % x for x in misnamed_file_list])
				print file_str
				message_html = HTML_BODY % file_str
				print message_html
				email_utils.send_email(os.path.join(settings.BASE_DIR, settings.GMAIL_CREDENTIALS), message_html, [project.owner.email,], '[CCCB] Error with Dropbox transfer')
			#callback = tasks.wrapup.s(project=project)
			[task.link_error(err_func) for task in all_transfers]
			print 'about to invoke callback'
			#callback = tasks.wrapup.s(kwargs={'project':project})
			callback = tasks.wrapup.s(kwargs={'project_pk': project.pk})
			#callback = tasks.wrapup.s(kwargs={'project_pk': project.pk}).on_error(tasks.on_chord_error.s())
			#callback = tasks.wrapup.s(kwargs={'project_pk': project.pk}).set(link_error='on_chord_error')
			print'about to do chord'
			r = chord(all_transfers)(callback)
			print 'done with chord'
		return HttpResponse('')
	except:
		return HttpResponseBadRequest('')
