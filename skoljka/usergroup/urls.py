from django.conf.urls.defaults import patterns

import skoljka.usergroup.views as views

urlpatterns = patterns(
    '',
    (r'^$', views.list_view),
    (r'^new/$', views.new),
    (r'^(?P<group_id>\d+)/$', views.detail),
    (r'^(?P<group_id>\d+)/edit/$', views.new),
    (r'^(?P<group_id>\d+)/members/$', views.members),
    (r'^(?P<group_id>\d+)/leave/$', views.leave),
)
