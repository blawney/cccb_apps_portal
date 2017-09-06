from __future__ import absolute_import, unicode_literals
from celery.decorators import task
import subprocess
import os
import email_utils
from django.conf import settings
import analysis_portal.helpers as helpers
from client_setup.models import Project

HTML_BODY = '<html><body>%s</body></html>'

@task(name='dropbox_transfer_to_bucket')
def dropbox_transfer_to_bucket(source_link, destination, project_pk):
	project = Project.objects.get(pk=project_pk)
	cmd = 'wget -q -O - "%s" | gsutil cp - gs://%s' % (source_link, destination)
	print cmd
	p = subprocess.Popen(cmd, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
	stdout, stderr = p.communicate()
	if p.returncode != 0:
		print 'Failed on transfering %s' % source_link.split('/')[-1]
		print stdout
		print '--'*10
		print stderr
		#message = 'our Dropbox file (%s) could not be determined. Please consult the instructions on how to name files for the application. Then try again.' % source_link.split('/')[-1]
	else:
		print 'Done transferring from %s' % source_link
		try:
			helpers.add_datasource_to_database(project, destination[len(project.bucket)+1:])
		except helpers.UndeterminedFiletypeException as ex:
		        project_owner = project.owner.email
			message = 'The file type of your Dropbox file (%s) could not be determined. Please consult the instructions on how to name files for the application. Then try again.' % source_link.split('/')[-1]
        		message_html = HTML_BODY % message
        		email_utils.send_email(os.path.join(settings.BASE_DIR, settings.GMAIL_CREDENTIALS), message_html, [project_owner,], '[CCCB] Problem with Dropbox transfer')
			raise ex

@task(name='wrapup')
def wrapup(x, kwargs):
	print 'in wrapup function, x=%s' % x
	print 'in wrapup function, kwargsX=%s' % kwargs
	project = Project.objects.get(pk=kwargs['project_pk'])
	project_owner = project.owner.email
	message = 'Your file transfer from Dropbox is complete! Return to the page or refresh'
	message_html = HTML_BODY % message
	email_utils.send_email(os.path.join(settings.BASE_DIR, settings.GMAIL_CREDENTIALS), message_html, [project_owner,], '[CCCB] Dropbox transfer complete')

@task(name='on_chord_error')
def on_chord_error(*args, **kwargs):
	print 'IN CHORD ERROR FUNCTION'
	print args
	print kwargs
	a0 = args[0]
	print a0
	print type(a0)
	print a0.args
