# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

from client_setup.models import Project

class Resource(models.Model):
        project = models.ForeignKey(Project)
        basename = models.CharField(max_length=500)
        public_link = models.CharField(max_length=1000)
        resource_type = models.CharField(max_length=100)
