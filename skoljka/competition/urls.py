from django.conf import settings
from django.conf.urls.defaults import patterns, url

import skoljka.competition.views as views
from skoljka.utils.string_operations import join_urls
from skoljka.utils.testutils import IS_TESTDB


def _make_patterns(patterns):
    result = []
    shorthands = settings.COMPETITION_URLS

    if IS_TESTDB:
        from skoljka.competition.tests.fixtures import TEST_COMPETITION_URLS

        shorthands = shorthands.copy()
        shorthands.update(TEST_COMPETITION_URLS)

    for competition_id, url_path_prefix in shorthands.iteritems():
        special = settings.COMPETITION_SPECIAL_URLS.get(competition_id, [])
        for _regex, view in list(patterns) + list(special):
            regex = '^' + join_urls(url_path_prefix, _regex)
            result.append(url(regex, view, {'competition_id': competition_id}))

    for _regex, view in patterns:
        # In case of a course, this link will redirect to the competition.
        regex = join_urls(r'^competition/(?P<competition_id>\d+)/', _regex)
        result.append(url(regex, view))

        # And vice versa.
        regex = join_urls(r'^course/(?P<competition_id>\d+)/', _regex)
        result.append(url(regex, view))

    return result


# Competition-related URLs, prefixed with competition_name/<id>/, competition/<id>/, or course/<id>/
_patterns = [
    # NOTE: Do not complicate here with names, as there might be multiple links
    # to the same competition page (with /competition/{{ id }}/ prefix and with
    # /{{ comp_prefix }}/). Use comp_url instead. Also, this is not a list
    # of url()s, the following list is first processed by _make_patterns.
    (r'$', views.homepage),
    (r'chain/$', views.chain_list),
    (r'chain/tasks/$', views.chain_tasks_list),
    (r'chain/tasks/action/$', views.chain_tasks_action),
    (r'chain/(?P<chain_id>\d+)/$', views.chain_edit),
    (r'chain/(?P<chain_id>\d+)/overview/$', views.chain_overview),
    (r'chain/new/$', views.chain_new),
    (r'notifications/$', views.notifications),
    (r'notifications/(?P<ctask_id>\d+)/$', views.notifications),
    (r'notifications/admin/$', views.notifications_admin),
    (r'participants/$', views.participants),
    (r'registration/$', views.registration),
    (r'rules/$', views.rules),
    (r'instructions/$', views.instructions),
    (r'scoreboard/$', views.scoreboard),
    (r'task/$', views.task_list),
    (r'task/new/$', views.task_new),
    (r'task/(?P<ctask_id>\d+)/$', views.task_detail),
    (r'submission/(?P<submission_id>\d+)/$', views.submission_detail),
    (r'task/(?P<ctask_id>\d+)/edit/$', views.task_new),
    (r'team/(?P<team_id>\d+)/$', views.team_detail),
    (r'team/list/admin/$', views.team_list_admin),
    (r'team/list/admin/confirm/$', views.team_list_admin_confirm),
]

_extra_urls = [
    (r'competition/$', 'competition_list'),
    (r'course/$', 'course_list'),
]

if IS_TESTDB:
    import skoljka.competition.tests.fixtures as _fixtures

    _patterns += [
        (r'test/create_chain/$', _fixtures.create_test_chain),
        (r'test/create_ctasks/$', _fixtures.create_test_ctasks),
        (r'test/create_team/$', _fixtures.create_test_team),
        (r'test/delete_teams/$', _fixtures.delete_teams),
        (r'test/update_competition/$', _fixtures.update_competition),
    ]
    _extra_urls += patterns(
        '',
        (r'^competition/test/fill/$', _fixtures.create_test_competitions),
        (r'^competition/test/update_chain/(?P<chain_id>\d+)/$', _fixtures.update_chain),
    )
    del _fixtures


urlpatterns = patterns(
    'skoljka.competition.views', *(_make_patterns(_patterns) + _extra_urls)
)
