# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import os
import re

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, SuspiciousOperation
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse

from client_setup.models import Project

@login_required
def cleanup(request):

	if request.method == 'GET':
		return render(request, 'cleanup/cleanup.html', {})
	elif request.method == 'POST':
		print 'received:\n'
		print request.POST
		return JsonResponse({'commands':['bar1', 'bar2', 'bar3']})
