# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
import random
import string
import json

from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest 
from django.contrib.auth.decorators import login_required
from google.cloud import storage
from django.contrib.auth.models import User
from forms import AddClientForm, ServiceForm
from models import Service, Project
from django.conf import settings
from django.core.exceptions import PermissionDenied

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
				project.save()

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
