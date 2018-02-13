# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import os
import re

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.template.loader import render_to_string
from client_setup.models import Project

from . import tasks

class DisplayObject(object):
	pass

@login_required
def remove_projects(request):
	if request.user.is_staff:
		pks_to_rm = request.session['pks_to_remove']
		tasks.rm_projects.delay(pks_to_rm)
		html = """
		<div class="alert alert-success" role="alert">
		  Removal has started.  Could take a bit of time.
		</div>
		"""
		return HttpResponse(html)
	else:
		raise PermissionDenied


@login_required
def cleanup(request):
	if request.user.is_staff:
		if request.method == 'GET':
			return render(request, 'cleanup/cleanup.html', {})
		elif request.method == 'POST':
			project_regex = request.POST.get('project_id_regex')
			pattern = re.compile(project_regex)
			all_projects = Project.objects.all()
			matched_projects = [p for p in all_projects if pattern.match(p.ilab_id)]
			pks_to_remove = [p.pk for p in matched_projects]
			request.session['pks_to_remove'] = pks_to_remove
			print 'to rm: %s' % pks_to_remove
			results = []
			for p in matched_projects:
				o = DisplayObject()
				o.bucket = p.bucket
				o.ilab_id = p.ilab_id
				o.owner = p.owner
				results.append(o)
			context = {'results':results}
			html = render_to_string('cleanup/result_snippet.html', context)
			return HttpResponse(html)
	else:
		raise PermissionDenied
