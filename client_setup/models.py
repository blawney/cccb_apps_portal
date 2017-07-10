# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User


class Organism(models.Model):
	reference_genome = models.CharField(max_length=50) # a brief name
	description = models.CharField(max_length=500) # a longer description
	def __str__(self):
		return self.reference_genome


class Service(models.Model):
	"""
	This is where we track the information about the various applications we host
	"""
	name = models.CharField(max_length=50) # a brief name
	description = models.CharField(max_length=500) # a longer description
	application_url = models.URLField()

	def __str__(self):
		return '%s (%s)' % (self.name, self.application_url)


class ProjectManager(models.Manager):
	def create_project(self, owner, service, bucket):
		project = self.create(owner=owner, service=service, bucket=bucket)
		return project


class Project(models.Model):
	"""
	Each request to the center is based around the concept of the project
	"""
	owner = models.ForeignKey(User)
	service = models.ForeignKey(Service)
	reference_organism = models.ForeignKey(Organism, blank=True, null=True)
	ilab_id = models.CharField(max_length=20, default='unknown')
	completed = models.BooleanField(default=False)
	paused_for_user_input = models.BooleanField(default=False)
	in_progress = models.BooleanField(default=False)
	status_message = models.CharField(max_length=50, default='')
	name = models.CharField(max_length=100, default='Unnamed project')
	start_time = models.DateTimeField(blank=True, null=True)
	finish_time = models.DateTimeField(blank=True, null=True)
	bucket = models.CharField(max_length=63) # default max length for a bucket is 63
	next_action_text = models.CharField(max_length = 100, default='')
	next_action_url = models.CharField(max_length = 255, default='')
	has_downloads = models.BooleanField(default=False)
	objects = ProjectManager()

	def __str__(self):
		return '%s (%s, %s)' % (self.name, self.owner, self.service)


class Sample(models.Model):
	"""
	This holds information about a sample.
	"""
	name = models.CharField(max_length=50, default="Unnamed sample")
	metadata = models.TextField(blank=True, null=True) # for the user, not really for us.  Lets them enter additional info beyond the name
	project = models.ForeignKey(Project)
	processed = models.BooleanField(default=False)

	class Meta:
		unique_together = (('project','name'),)

	def __str__(self):
		return self.name


class DataSource(models.Model):
	"""
	This is the information about the actual files.  They link back to a sample
	"""
	sample = models.ForeignKey(Sample, null=True, blank=True)
	project = models.ForeignKey(Project)
	# the types of files we can take:
	# the first value is what is stored in DB, the second is the 'display' value
	FILE_TYPES = (
		('fastq', 'FastQ'),
		('bam', 'BAM')
	)
	source_type = models.CharField(max_length=50, choices=FILE_TYPES)
	filepath = models.CharField(max_length=500)

	class Meta:
		unique_together = (('project','filepath'),)

	def __str__(self):
		return '%s' % self.filepath


