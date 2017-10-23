from django.core.urlresolvers import resolve
from django.http import HttpResponseBadRequest, Http404
from django.urls import reverse
from django.shortcuts import redirect
from client_setup.models import Project
from django.core.exceptions import ObjectDoesNotExist

# this is a module containing views that we want to prevent once the analysis has been started
# without this, we just end up in an infinite redirect loop
# we check to see if the requested view is in this list, and if it is (and in progress/complete conditions are met) then redirect
SETUP_VIEWS_MODULE = 'analysis_portal.setup_views'


class ProjecStatusMiddleWare(object):
	"""
	This middleware intercepts requests to check on the analysis status.  If the analysis has started or
	is complete, then send it to an appropriate view.  Otherwise, let the view process as usual
	"""   
	def __init__(self, get_response):
		self.get_response = get_response

	def process_view(self, request, view_func, view_args, view_kwargs):
		is_setup_view = False
		if view_func.__module__ == SETUP_VIEWS_MODULE:
			is_setup_view = True
		user = request.user

		# if requesting information about a specific project
		if 'project_pk' in view_kwargs:
			try:
				project_pk = int(view_kwargs['project_pk'])
				project = Project.objects.get(pk=project_pk)
				if project.owner == user:
					if project.in_progress and is_setup_view:
						return redirect('in_progress_view', project_pk = project_pk)
					elif project.completed and is_setup_view:
						return redirect('download_view', project_pk = project_pk)
					# to track the current step and maintain a single place to track the most recent page:
					service = project.service
					view_name = request.resolver_match.url_name
					try:
						current_workflow_step = service.workflow_set.get(step_url=view_name)
						project.step_number = current_workflow_step.step_order
						project.save()
					except ObjectDoesNotExist as ex:
						# If we are hitting a URL that is not one of the main workflow steps, then an exception will
						# be raised.  It's ok to let that one pass here
						pass
				else:
					print 'was not owner'
					raise Exception('Was not project owner')
			except ObjectDoesNotExist as ex:
				raise Http404()
			except Exception as ex:
				print 'ex message: %s' % ex.message
				return HttpResponseBadRequest('')								

	def __call__(self, request):
		return self.get_response(request)
