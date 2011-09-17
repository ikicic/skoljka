from django.conf.urls.defaults import patterns, include, url
from django.views.generic import DetailView, ListView, TemplateView
from task.models import Task
from solution.models import Solution

urlpatterns = patterns('',
    (r'^task/(?P<task_id>\d+)/submit/$', 'solution.views.submit'),
    (r'^solution/(?P<pk>\d+)/$',
        DetailView.as_view(
            model=Solution,
            template_name='solution_detail.html')),
    (r'^task/(?P<task_id>\d+)/user/(?P<user_id>\d+)/$', 'solution.views.solution_task_user')
)