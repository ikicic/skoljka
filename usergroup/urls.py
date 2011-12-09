from django.conf.urls.defaults import patterns, include, url
from django.contrib.auth.models import Group
from django.views.generic import DetailView

from usergroup.models import UserGroup

urlpatterns = patterns('',
    (r'^$', 'usergroup.views.list'),
    (r'^(?P<group_id>\d+)/', 'usergroup.views.detail'),
)
