# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponse
import datetime
import helpers

import sys
import os
sys.path.append(os.path.abspath('..'))
from rnaseq import rnaseq_process

from client_setup.models import Project

@login_required
def show_in_progress(request, project_pk):
	project = helpers.check_ownership(project_pk, request.user)
	if project:
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


def notify(request):
    """
    Called when a worker completes
    Each type of project may have different requirements on what information they need to send.
    """
    # at this endpoint, we only want to accept internal requests (from another GCE instance)
    user_ip = request.META['REMOTE_ADDR']
    print user_ip
    if user_ip.startswith('10.142'):
        project_pk = int(request.GET.get('projectPK', ''))
        print 'look for poejct with pk=%s' % project_pk
        try:
            project = Project.objects.get(pk = project_pk)
            print 'found project %s' % project
            if project.service.name == 'RNA-Seq':
                print 'found rnaseq project'
                rnaseq_process.handle(project, request)           
                print 'done handling'
                return HttpResponse('thanks')
            else:
                return HttpResponseBadRequest('')
        except Exception as ex:
            print 'threw exceptioni'
            print ex
            print ex.message
            return HttpResponseBadRequest('')
    else:
        print 'was not an internal rquest'
        return HttpResponseBadRequest('')
