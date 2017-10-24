# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
import random
import string
import json

from django.shortcuts import render
from django.urls import reverse
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest 
from django.contrib.auth.decorators import login_required
from google.cloud import storage
from django.contrib.auth.models import User
from forms import AddClientForm, ServiceForm
from models import Service, Project
from django.conf import settings
from django.core.exceptions import PermissionDenied

import os
import sys
sys.path.append(os.path.abspath('..'))
import email_utils

MESSAGE_TEMPLATE = """<html><body><p>An analysis project for iLab ID %s has been created for your email (%s).  
			You may now begin to upload files and perform analysis</p><p><a href="%s" target="_blank">Go to CCCB Applications.</a></p>
			<p>Note that your access will expire and <strong>files will be deleted in 30 days</strong> (on %s).</p>
			<p>Do NOT reply to this email. Email <a href="mailto:cccb@jimmy.harvard.edu">cccb@jimmy.harvard.edu</a> with questions or comments.</p>
			<p>CCCB Team</p>
			</body></html>"""
@login_required
def setup_client(request):

	if request.user.is_staff:
		# query the database for the services no matter what:
		service_list = Service.objects.all()
		service_dict = {x.name:x for x in service_list}
		if request.method == 'POST':
			client_form = AddClientForm(request.POST, prefix='client_form')
			if client_form.is_valid():
				first_name = client_form.cleaned_data['first_name']
				last_name = client_form.cleaned_data['last_name']
				email = client_form.cleaned_data['email_address']
	
				existing_users_with_email = User.objects.filter(email=email)
				previously_existed = existing_users_with_email.exists()
				if previously_existed:
					# user existed already, as identified by their email
					user = existing_users_with_email[0]
				else:
					user = User.objects.create_user(email, email, settings.DEFAULT_PWD)
					user.first_name = first_name
					user.last_name = last_name
					user.save()
				try:
					service = request.POST.get('service_select')
					svc = service_dict[service]

					ilab_id = request.POST.get('ilab_id')

					
					max_samples = int(request.POST.get('max_samples'))


				except KeyError:
					return HttpResponseBadRequest('')

				# create bucket
				storage_client = storage.Client()
				timestamp = datetime.datetime.now().strftime('%m%d%y-%H%M%S')
				client_pk = user.pk
				bucket_name = '%s-%s-%s' % (settings.BUCKET_PREFIX, client_pk, timestamp)
				try:
					print 'create bucket %s' % bucket_name
					bucket = storage_client.create_bucket(bucket_name)
					acl = bucket.acl
					url_signer_account_email = json.load(open(settings.URL_SIGNER_CREDENTIALS))['client_email']
					entity = acl.user(url_signer_account_email)
					entity.grant_owner()
					acl.save()
				except Exception as ex:
					print 'Something went wrong when creating the bucket'
					print ex.message
					return HttpResponseBadRequest('')	

				# create a Project, add client and bucket
				project = Project.objects.create_project(user, svc, bucket_name)
				project.ilab_id = ilab_id
				project.next_action_text = 'Upload files'
				project.max_sample_number = max_samples
				project.creation_date = datetime.datetime.now()
				project.save()

				workflow = svc.workflow_set.get(step_order=1)
				project.step_number = 0
				project.next_action_url = reverse(workflow.step_url, args=(project.pk,))
				project.save()

				now = project.creation_date
				delta = datetime.timedelta(days=settings.RETENTION_DAYS)
				later = now + delta
				msg = MESSAGE_TEMPLATE % (project.ilab_id, email, settings.HOST ,later.strftime('%B %d, %Y'))
				email_utils.send_email(os.path.join(settings.BASE_DIR, settings.GMAIL_CREDENTIALS), msg, [email, settings.CCCB_GROUP_EMAIL], '[CCCB] Analysis project created')

				# TODO send email
				if previously_existed:
					print 'You were already a user and we added another project.  go sign in.'
					success_message = 'Successfully added %s service for existing user %s %s (%s)' % (svc.name, first_name, last_name, email)
				else:
					success_message = 'Successfully added %s %s (%s) and created a %s service' % (first_name, last_name, email, svc.name)
		else:
			success_message = ''

		client_form = AddClientForm(prefix='client_form')

		return render(request, 'client_setup/add_client.html', {'client_form':client_form,  'message': success_message, 'services': service_list})	
	else: # user NOT staff
		#return HttpResponseBadRequest('')
		raise PermissionDenied
