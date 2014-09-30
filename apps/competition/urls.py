from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('competition.views',
    (r'^competition/(?P<competition_id>\d+)/$', 'homepage'),
    (r'^competition/(?P<competition_id>\d+)/registration/$', 'registration'),
    (r'^competition/(?P<competition_id>\d+)/rules/$', 'rules'),
    (r'^competition/(?P<competition_id>\d+)/scoreboard/$', 'scoreboard'),
    (r'^competition/(?P<competition_id>\d+)/task/$', 'task_list'),
    (r'^competition/(?P<competition_id>\d+)/task/(?P<ctask_id>\d+)/$', 'task_detail'),
    (r'^competition/(?P<competition_id>\d+)/chain/$', 'chain_list'),
    (r'^competition/(?P<competition_id>\d+)/chain/new/$', 'chain_new'),
    (r'^competition/(?P<competition_id>\d+)/chain/(?P<chain_id>\d+)/$', 'chain_edit'),
)
