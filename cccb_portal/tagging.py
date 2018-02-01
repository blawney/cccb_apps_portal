import json
import uuid
import subprocess
import os

from django.conf import settings

class GsutilException(Exception):
	pass

def tag_bucket(bucket_name, tag_dict):
	base_cmd = '%s label ch -l %s %s%s'

	for k, v in tag_dict.items():
		label = '%s:%s' % (k,v)
		cmd = base_cmd % (settings.GSUTIL_PATH, label, settings.GOOGLE_BUCKET_PREFIX, bucket_name)
		print 'CMD: %s' % cmd
		p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		stdout, stderr = p.communicate()
		if p.returncode != 0:
			print 'STDOUT was:\n %s' % stdout
			print 'STDERR was:\n %s' % stderr
			raise GsutilException('Problem setting label on bucket')
