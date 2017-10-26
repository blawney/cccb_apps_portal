from __future__ import absolute_import, unicode_literals
from celery.decorators import task
import subprocess

@task(name='finalize')
def finalize(project_pk):
	pass
