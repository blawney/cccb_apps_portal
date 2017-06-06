from client_setup.models import Project
from django.core.exceptions import ObjectDoesNotExist, SuspiciousOperation

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
