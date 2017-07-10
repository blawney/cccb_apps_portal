from client_setup.models import Project, Sample, DataSource
from django.core.exceptions import ObjectDoesNotExist, SuspiciousOperation
from django.http import HttpResponse, HttpResponseBadRequest
from django.conf import settings

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


def determine_filetype(filename):
	#TODO make the patterns into a dictionary so this could be more generalized
	basename = os.path.basename(filename)
	fq_match = re.search(settings.FASTQ_GZ_PATTERN, basename)
	if fq_match:
		return ('fastq', basename[:-len(fq_match.group(0))])
	bam_match = re.search(settings.BAMFILE_PATTERN, basename, re.IGNORECASE)
	if bam_match:
		return ('bam', basename[:-len(bam_match.group(0))])
	raise UndeterminedFiletypeException('Could not determine the filetype- please consult the instructions on naming your files.')


def add_datasource_to_database(project, newfile):
    """
    This updates the database
    """
    # see if it already exists:
    if DataSource.objects.filter(project=project, filepath=newfile).exists():
        # file was updated in google storage, but nothing to do here.  Return 204 so the front-end doesn't make more 'icons' for this updated file
        return HttpResponse(status=204)
    else:
        filetype, samplename = determine_filetype(newfile)

        new_ds = DataSource(project=project, source_type = filetype, filepath=newfile)
        new_ds.save()

        # check for existing sample
        project_samples = project.sample_set.all()
        if any([s.name==samplename for s in project_samples]):
            s = Sample.objects.get(project=project, name=samplename)
        else:
            s = Sample(name=samplename, metadata='', project=project)
            s.save()

        # add the datasource to the sample
        new_ds.sample = s
        new_ds.save()
        return HttpResponse('')
