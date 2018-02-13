import subprocess
from client_setup.models import Project
from celery.decorators import task

def run_cmd(cmd):
	p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	stdout,stderr = p.communicate()
	if p.returncode != 0:
		print 'STDOUT: %s' % stdout
		print 'STDERR: %s' % stderr

@task(name='rm_projects')
def rm_projects(pk_list):
	"""
	Receives a list of integers which are primary keys to Project objects
	in the database.  Removes them AND also issues gsutil commands to cleanup
	the storage
	"""
	for pk in pk_list:
		print 'Remove project with pk=%d' % pk
		p = Project.objects.get(pk=pk)
		bucket_name = p.bucket
		p.delete()

		rm_files_cmd = 'gsutil -m rm -r gs://%s/*' % bucket_name
		rm_bucket_cmd = 'gsutil rb gs://%s/' % bucket_name
		run_cmd(rm_files_cmd)
		run_cmd(rm_bucket_cmd)
