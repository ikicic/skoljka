from django.conf.urls.defaults import include, patterns, url
from django.contrib.auth.models import Group
from django.views.generic import DetailView

import skoljka.usergroup.views as views
from skoljka.usergroup.models import UserGroup

urlpatterns = patterns(
    '',
    (r'^$', views.list_view),
    (r'^new/$', views.new),
    (r'^(?P<group_id>\d+)/$', views.detail),
    (r'^(?P<group_id>\d+)/edit/$', views.new),
    (r'^(?P<group_id>\d+)/members/$', views.members),
    (r'^(?P<group_id>\d+)/leave/$', views.leave),
)
