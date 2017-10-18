# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.conf import settings

def pooled_crispr_setup_view(request, project_pk):
	context = {'project_id': project_pk, 'project_name':'Dummy project'}
	return render(request, 'pooled_crispr/setup.html', context)
