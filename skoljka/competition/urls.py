from django.conf import settings
from django.conf.urls.defaults import patterns, url

from skoljka.utils.string_operations import join_urls


def _make_patterns(*patterns):
    result = []
    shorthands = settings.COMPETITION_URLS
    for competition_id, url_path_prefix in shorthands.iteritems():
        special = settings.COMPETITION_SPECIAL_URLS.get(competition_id, [])
        for _regex, view in list(patterns) + list(special):
            regex = '^' + join_urls(url_path_prefix, _regex)
            result.append(url(regex, view, {'competition_id': competition_id}))

    for _regex, view in patterns:
        regex = join_urls(r'^competition/(?P<competition_id>\d+)/', _regex)
        result.append(url(regex, view))

    return result


# Competition-related URLs, prefixed with competition/<id>/
_patterns = _make_patterns(
    # NOTE: Do not complicate here with names, as there might be multiple links
    # to the same competition page (with /competition/{{ id }}/ prefix and with
    # /{{ comp_prefix }}/). Use comp_url instead. Also, this is not a list
    # of url()s, the following list is first processed by _make_patterns.
    (r'$', 'homepage'),
    (r'chain/$', 'chain_list'),
    (r'chain/tasks/$', 'chain_tasks_list'),
    (r'chain/tasks/action/$', 'chain_tasks_action'),
    (r'chain/(?P<chain_id>\d+)/$', 'chain_edit'),
    (r'chain/(?P<chain_id>\d+)/overview/$', 'chain_overview'),
    (r'chain/new/$', 'chain_new'),
    (r'notifications/$', 'notifications'),
    (r'notifications/(?P<ctask_id>\d+)/$', 'notifications'),
    (r'notifications/admin/$', 'notifications_admin'),
    (r'participants/$', 'participants'),
    (r'registration/$', 'registration'),
    (r'rules/$', 'rules'),
    (r'scoreboard/$', 'scoreboard'),
    (r'task/$', 'task_list'),
    (r'task/new/$', 'task_new'),
    (r'task/(?P<ctask_id>\d+)/$', 'task_detail'),
    (r'submission/(?P<submission_id>\d+)/$', 'submission_detail'),
    (r'task/(?P<ctask_id>\d+)/edit/$', 'task_new'),
    (r'team/(?P<team_id>\d+)/$', 'team_detail'),
)

_extra_urls = [
    (r'competition/$', 'competition_list'),
]

urlpatterns = patterns('skoljka.competition.views', *(_patterns + _extra_urls))
