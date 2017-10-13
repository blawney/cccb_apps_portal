# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest, HttpResponse
import datetime
import helpers

import sys
import os
sys.path.append(os.path.abspath('..'))
from rnaseq import rnaseq_process

from Crypto.Cipher import DES
import base64

from django.conf import settings
from client_setup.models import Project

@login_required
def show_in_progress(request, project_pk):
	project = helpers.check_ownership(project_pk, request.user)
	if project and project.in_progress:
		start_date = project.start_time.strftime('%b %d, %Y')
		start_time = project.start_time.strftime('%H:%M')
		time_str = 'Started on %s at %s' % (start_date, start_time)
		return render(request, 'analysis_portal/in_progress.html', {'project_name': project.name, 'time_str':time_str})
	else:
		return HttpResponseBadRequest('')


@login_required
def show_complete(request, project_pk):
	print 'in complete'
	project = helpers.check_ownership(project_pk, request.user)
	if project:
		start_date = project.start_time.strftime('%b %d, %Y')
		start_time = project.start_time.strftime('%H:%M')
		start_time_str = 'Started on %s at %s' % (start_date, start_time)

		finish_date = project.finish_time.strftime('%b %d, %Y')
		finish_time = project.finish_time.strftime('%H:%M')
		finish_time_str = 'Finished on %s at %s' % (finish_date, finish_time)
		return render(request, 'analysis_portal/complete.html', {'project_name': project.name, 'start_time_str':start_time_str, 'finish_time_str':finish_time_str})
	else:
		return HttpResponseBadRequest('')


def finish():
        print 'Do some final pulling together'

@csrf_exempt
def notify(request):
    """
    Called when a worker completes
    Each type of project may have different requirements on what information they need to send.
    """
    print request.POST
    if 'token' in request.POST:
        b64_enc_token = request.POST['token']
        enc_token = base64.decodestring(b64_enc_token)
        expected_token = settings.TOKEN
        obj=DES.new(settings.ENCRYPTION_KEY, DES.MODE_ECB)
        decrypted_token = obj.decrypt(enc_token)
        if decrypted_token == expected_token:
            print 'token matched'
            project_pk = int(request.POST.get('projectPK', ''))
            try:
                project = Project.objects.get(pk = project_pk)
                print 'found project %s' % project
                if project.service.name == 'rnaseq':
                    print 'found rnaseq project'
                    rnaseq_process.handle(project, request)
                    print 'done handling'
                    return HttpResponse('thanks')
                else:
                    return HttpResponseBadRequest('')
            except Exception as ex:
                print 'threw exception'
                print ex
                print ex.message
                return HttpResponseBadRequest('')
        else:
            print 'token did not match'
            return HttpResponseBadRequest('')
    else:
        print 'request did not have the required token to authenticate with'
        return HttpResponseBadRequest('')


@login_required
def problem(request, project_pk):
	project = helpers.check_ownership(project_pk, request.user)
	if project is not None:
		all_samples = project.sample_set.all()
		allowed_samples = project.max_sample_number
		return render(request, 'analysis_portal/problem.html', {'project_pk':project.pk, 'project_name':project.name, 'allowed_samples':allowed_samples, 'total_samples':len(all_samples)})
        else:
                return HttpResponseBadRequest('')
