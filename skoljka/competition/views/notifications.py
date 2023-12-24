import re

from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _

from skoljka.competition.decorators import competition_view
from skoljka.competition.models import Competition, CompetitionTask, Team, TeamMember
from skoljka.competition.utils import get_teams_for_user_ids
from skoljka.mathcontent.latex import latex_escape
from skoljka.permissions.constants import EDIT
from skoljka.post.forms import PostsForm
from skoljka.post.models import Post
from skoljka.utils.decorators import response

__all__ = ['notifications', 'notifications_admin']


@competition_view()
@response('competition_notifications.html')
def notifications(request, competition, data, ctask_id=None):
    team = data['team']

    # This could return None as a member, but that's not a problem.
    member_ids = set(
        TeamMember.objects.filter(team=team).values_list('member_id', flat=True)
    )

    posts = list(competition.posts.select_related('author', 'content'))
    if team:
        team_posts = list(team.posts.select_related('author', 'content'))
        for post in team_posts:
            post.t_team = team
        posts += team_posts
        post_form = team.posts.get_post_form()
        if ctask_id is not None:
            ctask = get_object_or_404(
                CompetitionTask.objects.select_related('chain'), id=ctask_id
            )
            ctask.competition = competition
            post_form.fields['text'].initial = _notification_ctask_prefix(
                ctask, data['is_admin']
            )
        data['post_form'] = post_form

    posts.sort(key=lambda post: post.date_created, reverse=True)

    data['posts'] = posts
    data['target_container'] = team
    data['team_member_ids'] = member_ids
    return data


@competition_view(permission=EDIT)
@response('competition_notifications_admin.html')
def notifications_admin(request, competition, data):
    team_ct = ContentType.objects.get_for_model(Team)
    teams = Team.objects.filter(competition=competition)
    team_ids_query = teams.values_list('id', flat=True)

    if request.method == 'POST':
        # Handle post hide/show (mark as answered/unanswered).
        # We use `extra == 0` as unanswered, `extra == 1` as answered.
        action = request.POST.get('action', '')
        match = re.match(r'(show|hide)-(\d+)', action)
        if match:
            post_id = int(match.group(2))
            extra = 1 if match.group(1) == 'hide' else 0

            # Update if competition-related post.
            competition.posts.filter(id=post_id).update(extra=extra)

            # Update if team-related post. As noted below, using
            # `team__competition_id` makes one JOIN too much.
            Post.objects.filter(
                id=post_id, content_type=team_ct, object_id__in=team_ids_query
            ).update(extra=extra)

    show_answered = request.GET.get('answered') == '1'
    extra_filter = {} if show_answered else {'extra': 0}

    posts = list(
        competition.posts.filter(**extra_filter).select_related('author', 'content')
    )
    teams = list(teams)
    teams_dict = {x.id: x for x in teams}
    # Post.objects.filter(team__competition_id=id, ct=...) makes an extra JOIN.
    team_posts = list(
        Post.objects.filter(
            content_type=team_ct, object_id__in=team_ids_query, **extra_filter
        ).select_related('author', 'content')
    )
    user_ids = [post.author_id for post in team_posts]
    user_id_to_team = get_teams_for_user_ids(competition, user_ids)
    for post in team_posts:
        post.t_team = user_id_to_team.get(post.author_id)
        if post.t_team:
            post.t_team.competition = competition
        post.t_target_team = teams_dict.get(post.object_id)
        if post.t_target_team:
            post.t_target_team.competition = competition

    post_form = PostsForm(placeholder=_("Message"))
    if 'ctask' in request.GET:
        try:
            ctask = CompetitionTask.objects.get(
                competition=competition, id=request.GET['ctask']
            )
        except CompetitionTask.DoesNotExist:
            pass
        else:
            post_form.fields['text'].initial = _notification_ctask_prefix(
                ctask, data['is_admin']
            )
    if 'team' in request.GET:
        try:
            selected_team_id = int(request.GET['team'])
        except ValueError:
            pass
        else:
            for team in teams:
                if team.id == selected_team_id:
                    data['selected_team_id'] = selected_team_id
                    team.t_selected_attr = ' selected="selected"'
                    break
    if 'ctask' in request.GET or 'team' in request.GET:
        post_form.fields['text'].widget.attrs['autofocus'] = 'autofocus'

    posts += team_posts
    posts.sort(key=lambda post: post.date_created, reverse=True)

    data.update(
        {
            'competition_ct': ContentType.objects.get_for_model(Competition),
            'post_form': post_form,
            'posts': posts,
            'show_answered': show_answered,
            'team_ct': team_ct,
            'teams': teams,
        }
    )
    return data


def _notification_ctask_prefix(ctask, is_admin):
    task_link = u'[b]{} [url={}]{}[/url][/b]\n\n'.format(
        _("Task:"), ctask.get_absolute_url(), latex_escape(ctask.get_name())
    )
    if is_admin:
        return task_link
    return task_link + _("Write the question / message here.")
