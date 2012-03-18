from django.conf.urls.defaults import patterns, include, url
from django.contrib.auth.models import Group
from django.views.generic import DetailView

from usergroup.models import UserGroup

urlpatterns = patterns('',
    (r'^$', 'usergroup.views.list'),
    (r'^new/$', 'usergroup.views.new'),
    (r'^(?P<group_id>\d+)/$', 'usergroup.views.detail'),
    (r'^(?P<group_id>\d+)/edit/$', 'usergroup.views.new'),
    (r'^(?P<group_id>\d+)/members/$', 'usergroup.views.members'),
    (r'^(?P<group_id>\d+)/leave/$', 'usergroup.views.leave'),
)
