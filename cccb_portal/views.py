# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
import urllib
import httplib2  
import json
import hashlib
import os
import json

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as django_login
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse

@login_required
def index(request):
	# this will direct users to the login page
	return redirect('/login/')

@login_required
def dummy_view(request):
	print 'in dummy view'
	print request
	print request.user
	print 'x'*50
	print request.session.get('drive_credentials', None)
	print 'x'*50

	from apiclient.http import MediaIoBaseDownload
        from apiclient.discovery import build
	from oauth2client.client import OAuth2Credentials
        credentials = request.session.get('drive_credentials', None)
        credentials = OAuth2Credentials.from_json(credentials)
        http_auth = credentials.authorize(httplib2.Http())
        drive_service = build('drive', 'v3', http=http_auth)
	all_files = json.loads(request.POST.get('transfers'))
	print all_files
	for file_id, file_name in all_files.items():
		drive_request = drive_service.files().get_media(fileId=file_id)
		with open(os.path.join(settings.TEMP_DIR, file_name), 'wb') as fh:
			downloader = MediaIoBaseDownload(fh, drive_request)
			done = False
			while done is False:
				status, done = downloader.next_chunk()


	return HttpResponse('')


def unauthorized(request):
	return HttpResponse('This user has not been authorized by the CCCB', status=403)

def login(request):
    return render(request, 'account/login.html', {})    

def google_login(request):
	"""
	Starts the auth flow with google
	"""
	token_request_uri = settings.GOOGLE_AUTH_ENDPOINT
	response_type = "code"

	# for validating that we're not being spoofed
	state = hashlib.sha256(os.urandom(1024)).hexdigest()
	request.session['session_state'] = state

	url = "{token_request_uri}?response_type={response_type}&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&state={state}".format(
        token_request_uri = token_request_uri,
        response_type = response_type,
        client_id = settings.GOOGLE_CLIENT_ID,
        redirect_uri = settings.GOOGLE_REGISTERED_CALLBACK,
        scope = settings.AUTH_SCOPE,
        state = state)

	print 'made url: %s' % url
	print '*'*200
	return HttpResponseRedirect(url)

def oauth2_callback(request):
	"""
	This is the view that Google calls back as part of the OAuth2 flow
	"""
	print 'in callback'
	parser = httplib2.Http()

	if 'error' in request.GET or 'code' not in request.GET:
		return HttpResponseRedirect(reverse('unauthorized'))

	if request.GET['state'] != request.session['session_state']:
        	return HttpResponseRedirect(reverse('unauthorized')) 

	params = urllib.urlencode({
        	'code':request.GET['code'],
        	'redirect_uri':settings.GOOGLE_REGISTERED_CALLBACK,
        	'client_id':settings.GOOGLE_CLIENT_ID,
        	'client_secret':settings.GOOGLE_CLIENT_SECRET,
        	'grant_type':'authorization_code'
	})
	headers={'content-type':'application/x-www-form-urlencoded'}
	resp, content = parser.request(settings.ACCESS_TOKEN_URI, method = 'POST', body = params, headers = headers)
	c = json.loads(content)
	print 'received %s' % c
	token_data = c['access_token']
	token_uri = '%s?access_token=%s' % (settings.USER_INFO_URI, token_data)
	resp, content = parser.request(token_uri)
	content = json.loads(content)
	is_verified = content['verified_email']    
	email = content['email']
	print 'got email: %s' % email
	if is_verified:
		try:
			user = User.objects.get(email=email)
			django_login(request, user)
			return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
		except ObjectDoesNotExist as ex:
			return HttpResponseRedirect(reverse('unauthorized'))
