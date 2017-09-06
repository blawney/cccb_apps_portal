# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, SuspiciousOperation

from client_setup.models import Project
from models import Resource 

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
            o.append({"text": key, "href": value, "state":{"expanded": 1}})
    return o
