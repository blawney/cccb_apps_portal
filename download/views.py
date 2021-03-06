# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, SuspiciousOperation

from client_setup.models import Project
from models import Resource, ResourceDownload

EXPIRED_LINK_MARKER = '#' 

def check_ownership(project_pk, user):
    """
    Checks the ownership of a requested project (addressed by its db primary key)
    Returns None if the project is not found or some other exception is thrown
    Since this is not called directly, we cannot return any httpresponses directly to the client
    """
    try:
        project_pk = int(project_pk)
        print 'about to query project'
        project = Project.objects.get(pk=project_pk)
        if project.owner == user:
            return project
        else:
            return None # if not the owner
    except ObjectDoesNotExist as ex:
        raise SuspiciousOperation
    except:
        return None # if exception when parsing the primary key (or non-existant pk requested)


def check_not_downloaded(d, user):
	"""
	Checks the database table for whether a resource has been downloaded already by this user
	Note that the sorted_dict is of the following format:
	{
		'BAM files':{
				'fileA.bam':'https://storage.cloud.google.com/....',
				'fileA.bam':'https://storage.cloud.google.com/....',
				'fileA.bam':'https://storage.cloud.google.com/....',
		}
		'compressed':{
			'fileA.zip':'https://storage.cloud.google.com/....'
		}
	}
	Since we no longer have Resource objects, we use the https://storage.cloud.google.com/... links as unique identifiers for the files
	"""
	users_downloads = ResourceDownload.objects.filter(downloader = user)
	link_dict = {x.resource.public_link:x.download_date for x in users_downloads} # now have a dict of links that have been downloaded
	for filetype, files_dict in d.items():
		for basename, link in files_dict.items():
			if link in link_dict:
				download_time = link_dict[link]

				# drop the existing entry
				files_dict.pop(basename)

				# make another descriptive name to indicate file was downloaded already:
				newname = '%s (downloaded %s)' % (basename, download_time.strftime('%b %d, %Y'))
				files_dict[newname] = EXPIRED_LINK_MARKER


@login_required
def download_view(request, project_pk):
    project = check_ownership(project_pk, request.user)
    if project:
        objects = Resource.objects.filter(project=project)
        d = {} # a dict of dicts
        for o in objects:
            try:
                d[o.resource_type].update({o.basename:o.public_link})
            except KeyError:
                d[o.resource_type] = {o.basename:o.public_link}
 
        # want to check that files were not already downloaded:
        check_not_downloaded(d, request.user)

        tree = reformat_dict(d)
        return render(request, 'download/download_page.html', {
                'tree':json.dumps(tree) if tree else tree})
    else:
        return HttpResponseBadRequest('')


def reformat_dict(d):
    """
    Reformats the dictionary to follow the required format for the UI
    """
    o = []
    for key, value in d.items():
        if type(value) is dict:
            rv =reformat_dict(value)
            new_d = {"text": key, "nodes":rv, "state":{"expanded": 1}}
            o.append(new_d)
        else:
		if value == EXPIRED_LINK_MARKER:
			o.append({"text": key, "selectable":0, "state":{"expanded": 1, "disabled":1}})
		else:
			o.append({"text": key, "href": value, "state":{"expanded": 1}})
    return o
