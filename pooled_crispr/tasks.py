from __future__ import absolute_import, unicode_literals
from celery.decorators import task
from google.cloud import storage
from django.conf import settings
from download.models import Resource
from client_setup.models import Project
import pooled_crispr.config_parser as cp_
import email_utils
import subprocess
import re
import os
from django.conf import settings

LINK_ROOT = settings.PUBLIC_STORAGE_ROOT + '%s/%s'

@task(name='finalize')
def finalize(project_pk):

	project = Project.objects.get(pk=project_pk)
	bucket_name = project.bucket
	storage_client = storage.Client()
	bucket = storage_client.get_bucket(bucket_name)
	all_contents = bucket.list_blobs()
	all_contents = [x for x in all_contents] # turn iterator into list

	config_params = cp_.parse_config()
	
	# get the files that are in the result folder:
	outfiles = {}
	outfiles['BAM Files'] = []
	bam_pattern = '%s/.*.bam$' % config_params['output_bucket']
        outfiles['BAM Files'].extend([x for x in all_contents if re.match(bam_pattern, x.name) is not None])
	bai_pattern = '%s/.*.bam.bai$' % config_params['output_bucket']
        outfiles['BAM Files'].extend([x for x in all_contents if re.match(bai_pattern, x.name) is not None])

	outfiles['Quantification table'] = [x for x in all_contents if x.name == os.path.join(config_params['output_bucket'], config_params['merged_counts_filename'])]
	
	# add user's privileges to these:
	for key, filelist in outfiles.items():
		for f in filelist:
			print 'grant ownership on %s' % f
			acl = f.acl
			entity = acl.user(project.owner.email)
			entity.grant_read()
			acl.save()

			# register the files with the download app
			public_link = LINK_ROOT % (bucket.name, f.name)
			r = Resource(project=project, basename = os.path.basename(f.name), public_link = public_link, resource_type = key)
			r.save()

			set_meta_cmd = 'gsutil setmeta -h "Content-Disposition: attachment; filename=%s" gs://%s/%s' % (os.path.basename(f.name), bucket_name, f.name)
			print 'set meta cmd: %s' % set_meta_cmd
			process = subprocess.Popen(set_meta_cmd, shell = True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
			stdout, stderr = process.communicate()
			if process.returncode != 0:
				print 'Error while setting metadata on %s. STDERR was:\n %s' % (f.name, stderr)

	print 'send notification email'
	message_html = write_completion_message(project)
	email_utils.send_email(os.path.join(settings.BASE_DIR, settings.GMAIL_CREDENTIALS), message_html, [project.owner.email,], 'Your pooled CRISPR analysis has completed')


def write_completion_message(project):
    message_html = """\
    <html>
      <head></head>
      <body>
          <p>
            Your pooled CRISPR analysis (%s) is complete!  Log-in to the CCCB application site at <a href="%s">%s</a> to view and download your results.
          </p>
      </body>
    </html>
    """ % (project.name, settings.HOST, settings.HOST)
    return message_html

