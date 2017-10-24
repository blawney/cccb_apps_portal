# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.conf import settings

def pooled_crispr_library_view(request, project_pk):
	context = {}
	return render(request, 'pooled_crispr/upload.html', context)

def pooled_crispr_summary_view(request, project_pk):
	context = {}
	return render(request, 'pooled_crispr/summary.html', context)
