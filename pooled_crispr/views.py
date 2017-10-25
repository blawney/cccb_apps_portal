# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.conf import settings

import sys
sys.path.append(os.path.abspath('..'))
from analysis import setup_views, helpers


def pooled_crispr_fastq_upload(request, project_pk):
	return setup_views.upload_page(request, project_pk)

def pooled_crispr_library_upload(request, project_pk):
	return setup_views.upload_page(request, project_pk)

@login_required
def pooled_crispr_summary_view(request, project_pk):
	"""
	Summarizes the project prior to performing the analysis
	"""
	project = helpers.check_ownership(project_pk, request.user)
	if project is not None:
		full_mapping = {}
		all_samples = project.sample_set.all()
		for s in all_samples:
			data_sources = s.datasource_set.all()
			full_mapping[s] = ', '.join([os.path.basename(x.filepath) for x in data_sources])
			previous_url, next_url = helpers.get_bearings(project)
			context = {'mapping':full_mapping, \
				'project_pk':project.pk, \
				'project_name':project.name,\
				'previous_page_url':previous_url, \
				'next_page_url':next_url \
			}
		return render(request, 'pooled_crispr/summary.html', context)
	else:
		return HttpResponseBadRequest('')
