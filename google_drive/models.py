# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class DriveUserCredentials(models.Model):
        """
	JSON credentials for user's Drive
        """
        owner = models.OneToOneField(User)
	json_credentials = models.CharField(max_length=5000, default='')
