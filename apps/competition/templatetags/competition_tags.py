from django import template
from django.contrib.auth.models import User
from django.utils.html import mark_safe

from competition.models import TeamMember
from competition.utils import get_ctask_statistics

import json

register = template.Library()

@register.simple_tag(takes_context=True)
def comp_url(context, url_name):
    competition = context['competition']
    # TODO: do it the proper way
    suffix = '/' if url_name else ''
    return competition.get_absolute_url() + url_name + suffix

@register.simple_tag(takes_context=True)
def cdebug(context, var):
    return dir(var)

@register.simple_tag(takes_context=True)
def reg_available_users(context):
    in_teams = TeamMember.objects \
            .filter(team__competition_id=context['competition'].id, \
                    invitation_status=TeamMember.INVITATION_ACCEPTED) \
            .exclude(member_id__isnull=True) \
            .values_list('member_id', flat=True)

    # exclude 'arhiva' account and the current user
    in_teams = list(in_teams) + [1, context['user'].id]
    available = list(User.objects.filter(is_active=True) \
            .exclude(id__in=in_teams) \
            .values_list('username', 'id'))
    available.sort()

    return mark_safe(u'<script>reg_available_users={{{}}};</script>'.format(
            u','.join(u'"{}":{}'.format(username, user_id) for
                username, user_id in available)))

@register.simple_tag(takes_context=True)
def reg_add_member_fields(context):
    user = context['request'].user
    competition = context['competition']
    team = context.get('team', None)

    if team:
        team_members = list(TeamMember.objects.filter(team=team) \
                .exclude(member_id=user.id) \
                .values_list('member_name', 'member_id', 'invitation_status'))
    else:
        team_members = []

    for k in xrange(len(team_members) + 1, competition.max_team_size + 1):
        team_members.append(('', '', TeamMember.INVITATION_UNANSWERED))

    output = []
    for k in xrange(len(team_members) - 1):
        member_name, member_id, status = team_members[k]
        output.append(u'reg_add_member_field({},"{}",{},{});'.format(
            k + 2, member_name, member_id or 0,
            int(status == TeamMember.INVITATION_ACCEPTED)))

    return u"<script>{}</script>".format(u''.join(output))

@register.simple_tag(takes_context=True)
def ctask_statistics_json(context):
    stats = get_ctask_statistics(context['competition'])
    return json.dumps(stats)

@register.simple_tag()
def ctask_class(ctask):
    if ctask.t_is_locked:
        return "ctask-locked"
    if ctask.t_is_solved:
        return "bar ctask-solved"
    if ctask.t_submission_count == 0:
        return "bar ctask-open"
    if ctask.t_submission_count >= ctask.max_submissions:
        return "bar ctask-failed"
    return "bar ctask-tried"

@register.simple_tag()
def chain_badge_class(chain):
    if all(ctask.t_is_solved for ctask in chain.ctasks):
        return "badge-success"
    if any(ctask.t_submission_count > ctask.max_submissions \
            for ctask in chain.ctasks):
        return ""
    return "badge-info"

@register.simple_tag()
def legend_ctask(_class, text):
    return mark_safe(
            u'<tr>' \
                u'<td width="100%">' \
                    u'<div class="progress"><div class="{}"></div></div>' \
                u'</td>' \
                u'<td>{}</td>' \
            u'</tr>'.format(_class, text))

@register.simple_tag()
def legend_chain(_class, text):
    return mark_safe(
            u'<tr>' \
                u'<td width="100%"><span class="badge {}">+1</span></td>' \
                u'<td>{}</td>' \
            u'</tr>'.format(_class, text))

@register.simple_tag(takes_context=True)
def team_score(context, team):
    """Outputs formatted team score.

    Takes into account if the scoreboard is frozen, were there any submissions
    after the freeze, is the current user a member of the given team or if it
    is a competition admin.
    """
    result = str(team.cache_score)
    if context['is_scoreboard_frozen']:
        before = team.cache_score_before_freeze
        max_after = team.cache_max_score_after_freeze
        if before != max_after:
            result += " (+{}?)".format(max_after - before)
            if context['team'] == team or context['is_admin']:
                result += " ({})".format(team.cache_score)
    return result
