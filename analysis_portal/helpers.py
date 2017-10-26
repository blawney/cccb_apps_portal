from client_setup.models import Project, Sample, DataSource, SampleDataSource
from django.core.exceptions import ObjectDoesNotExist, SuspiciousOperation
from django.http import HttpResponse, HttpResponseBadRequest
from django.conf import settings
from django.urls import reverse
import os
import re

class UndeterminedFiletypeException(Exception):
	pass

def check_ownership(project_pk, user):
	"""
	Checks the ownership of a requested project (addressed by its db primary key)
	Returns None if the project is not found or some other exception is thrown
	Since this is not called directly, we cannot return any httpresponses directly to the client
	"""
	try:
		project_pk = int(project_pk)
		project = Project.objects.get(pk=project_pk)
		if project.owner == user:
			return project
		else:
			return None # if not the owner
	except ObjectDoesNotExist as ex:
		raise SuspiciousOperation
	except:
		return None # if exception when parsing the primary key (or non-existant pk requested)


def determine_filetype(filename):
	#TODO make the patterns into a dictionary so this could be more generalized
	basename = os.path.basename(filename)

	fq_match = re.search(settings.FASTQ_GZ_PATTERN, basename)
	if fq_match:
		return ('fastq', basename[:-len(fq_match.group(0))])

	bam_match = re.search(settings.BAMFILE_PATTERN, basename, re.IGNORECASE)
	if bam_match:
		return ('bam', basename[:-len(bam_match.group(0))])

	excel_match = re.search(settings.EXCEL_PATTERN, basename, re.IGNORECASE)
	if excel_match:
		return ('excel', basename[:-len(excel_match.group(0))])

	tsv_match = re.search(settings.TSV_PATTERN, basename, re.IGNORECASE)
	if tsv_match:
		return ('tsv', basename[:-len(tsv_match.group(0))])

	csv_match = re.search(settings.CSV_PATTERN, basename, re.IGNORECASE)
	if csv_match:
		return ('csv', basename[:-len(csv_match.group(0))])

	raise UndeterminedFiletypeException('Could not determine the filetype- please consult the instructions on naming your files.')


def add_datasource_to_database(project, newfile, is_sample_datasource_upload):
    """
    This updates the database
    """
    # see if it already exists:
    if DataSource.objects.filter(project=project, filepath=newfile).exists():
        # file was updated in google storage, but nothing to do here.  Return 204 so the front-end doesn't make more 'icons' for this updated file
        return HttpResponse(status=204)
    else:
        filetype, samplename = determine_filetype(newfile)

        if is_sample_datasource_upload:
            print 'was datasource related to a sample'
            new_ds = SampleDataSource(project=project, source_type = filetype, filepath=newfile)
            new_ds.save()
        else:
            print 'was a sample-agnostic datasource'
            new_ds = DataSource(project=project, source_type = filetype, filepath=newfile)
            new_ds.save()

        # add the datasource to the sample if it's actually a sample-related datasource
        if is_sample_datasource_upload:
            print 'since datasource was related to a sample, create one if it does not exist'
            # check for existing sample
            project_samples = project.sample_set.all()
            if any([s.name==samplename for s in project_samples]):
                s = Sample.objects.get(project=project, name=samplename)
            else:
                s = Sample(name=samplename, metadata='', project=project)
                s.save()
            new_ds.sample = s
            new_ds.save()
        return HttpResponse('')


def get_bearings(project):
	"""
	Uses the current URL to determine which step in the workflow we are at.
	Determines the URLs to the previous and next steps in the workflow
	returns a tuple of previous url and next url 
	"""
	# Note that there is middleware looking at the request and determining the current
	# workflow step based on the requested url.  The Project object has its step_number
	# attribute set accordingly.
	service = project.service
	current_step = project.step_number
	next_step_number = current_step + 1
	previous_step_number = current_step -1 if current_step >=1 else 0

	# if previous page was the home/dashboard, just use a reverse url resolver without a primary key for the project
	previous_workflow_step = service.workflow_set.get(step_order=previous_step_number)
	previous_url_name = previous_workflow_step.step_url
	if previous_step_number == 0:
		previous_url = reverse(previous_url_name)
	else:
		previous_url = reverse(previous_url_name, args=(project.pk,))

	try:
		next_workflow_step = service.workflow_set.get(step_order=next_step_number)
		next_url_name = next_workflow_step.step_url
		next_url = reverse(next_url_name, args=(project.pk,))
	except ObjectDoesNotExist as ex:
		next_url = ''
	return (previous_url, next_url)
