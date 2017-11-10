import json
import uuid
import subprocess
import os

from django.conf import settings

class GsutilException(Exception):
	pass

def tag_bucket(bucket_name, tag_dict):
	base_cmd = '%s label set %s %s%s'

	# make a json file in a temp location
	uuid_obj = uuid.uuid4()
	uuid_str = str(uuid_obj)
	try:
		os.makedirs(settings.TEMP_DIR)
	except OSError as ex:
		if ex.errno == 17:
			pass
		else:
			print ex.message
			raise ex

	tmp_json_path = os.path.join(settings.TEMP_DIR, uuid_str + '.json')
	json.dump( tag_dict, open(tmp_json_path, 'w'))


	cmd = base_cmd % (settings.GSUTIL_PATH, tmp_json_path, settings.GOOGLE_BUCKET_PREFIX, bucket_name)

	print 'CMD: %s' % cmd
	p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	stdout, stderr = p.communicate()
	if p.returncode != 0:
		print 'STDOUT was:\n %s' % stdout
		print 'STDERR was:\n %s' % stderr
		raise GsutilException('Problem setting label on bucket')
