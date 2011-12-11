from django.conf.urls.defaults import patterns, include, url
from django.views.generic import DetailView, ListView, TemplateView

urlpatterns = patterns('',
    (r'^$', 'pm.views.inbox'),
    (r'^outbox/$', 'pm.views.outbox'),
    (r'^new/$', 'pm.views.new'),
    (r'^new/(?P<rec>[^/]+)/$', 'pm.views.new'),
    (r'^group/(?P<group_id>\d+)/$', 'pm.views.group_inbox'),
)
