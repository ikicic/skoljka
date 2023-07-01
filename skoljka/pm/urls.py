from django.conf.urls.defaults import include, patterns, url
from django.views.generic import DetailView, ListView, TemplateView

import skoljka.pm.views as views

urlpatterns = patterns(
    '',
    (r'^$', views.inbox),
    (r'^outbox/$', views.outbox),
    (r'^new/$', views.new),
    (r'^new/(?P<rec>[^/]+)/$', views.new),
    (r'^group/(?P<group_id>\d+)/$', views.group_inbox),
    (r'^(?P<id>\d+)/reply/$', views.pm_action),
    (r'^(?P<id>\d+)/replyall/$', views.pm_action),
    (r'^(?P<id>\d+)/forward/$', views.pm_action),
    (r'^(?P<id>\d+)/delete/$', views.pm_action),
)
