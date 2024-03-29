import json
import re
import urllib

from django import template
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.template.defaultfilters import truncatechars
from django.utils.html import mark_safe
from django.utils.translation import ungettext

from skoljka.activity import action as _action
from skoljka.activity.models import Action
from skoljka.competition.models import Submission, TeamMember
from skoljka.competition.utils import comp_url as utils__comp_url
from skoljka.competition.utils import ctask_comment_class as utils__ctask_comment_class
from skoljka.competition.utils import get_ctask_statistics, parse_chain_comments_cache
from skoljka.userprofile.templatetags.userprofile_tags import userlink
from skoljka.utils import xss

register = template.Library()


@register.simple_tag(takes_context=True)
def comp_url(context, *parts):
    return utils__comp_url(context['competition'], *parts)


@register.simple_tag(takes_context=True)
def competition_scoreboard_url(context, key, value):
    """Return a scoreboard URL with an additional key=value GET parameter."""
    get_params = context['request'].GET.copy()
    get_params[key] = value
    return '?' + get_params.urlencode()


@register.simple_tag(takes_context=True)
def cdebug(context, var):
    return dir(var)


@register.simple_tag(takes_context=True)
def reg_available_users(context):
    in_teams = (
        TeamMember.objects.filter(
            team__competition_id=context['competition'].id,
            invitation_status=TeamMember.INVITATION_ACCEPTED,
        )
        .exclude(member_id__isnull=True)
        .values_list('member_id', flat=True)
    )

    # exclude 'arhiva' account and the current user
    in_teams = list(in_teams) + [1, context['user'].id]
    available = list(
        User.objects.filter(is_active=True)
        .exclude(id__in=in_teams)
        .values_list('username', flat=True)
    )

    return mark_safe(
        u'<script>reg_available_users=[{}];</script>'.format(
            u','.join(u'"{}"'.format(username) for username in available)
        )
    )


@register.simple_tag(takes_context=True)
def reg_add_member_fields(context):
    user = context['request'].user
    competition = context['competition']
    team = context.get('team', None)

    if team:
        team_members = list(
            TeamMember.objects.filter(team=team)
            .exclude(member_id=user.id)
            .values_list('member_name', 'member_id', 'invitation_status')
        )
    else:
        team_members = []

    for k in range(len(team_members) + 1, competition.max_team_size + 1):
        team_members.append(('', '', TeamMember.INVITATION_UNANSWERED))

    output = []
    for k in range(len(team_members) - 1):
        member_name, member_id, status = team_members[k]
        # If member_id isn't None, member_name is the same as username.
        output.append(
            u'reg_add_member_field({},"{}","{}",{});'.format(
                k + 2,
                member_name,
                member_name if member_id else '',
                int(status == TeamMember.INVITATION_ACCEPTED),
            )
        )

    return u"<script>{}</script>".format(u''.join(output))


@register.simple_tag(takes_context=True)
def ctask_statistics_json(context):
    # TODO: This shouldn't be a template tag.
    stats = get_ctask_statistics(context['competition'].id)
    return json.dumps(stats)


@register.simple_tag(takes_context=True)
def ctask_class(context, ctask):
    if ctask.t_is_locked:
        return "ctask-locked"
    if ctask.t_is_solved:
        return "bar ctask-solved"
    if ctask.chain.is_closed(minutes_passed=context['minutes_passed']):
        return "bar ctask-closed"
    if ctask.t_submission_count == 0:
        return "bar ctask-open"
    if ctask.t_submission_count >= ctask.max_submissions:
        return "bar ctask-failed"
    return "bar ctask-attempted"


@register.simple_tag(takes_context=True)
def chain_ctask_comments_info(context, chain):
    num_important, num_important_my = parse_chain_comments_cache(chain, context['user'])
    if num_important:
        first = ungettext("%d important", "%d important", num_important) % num_important
        if num_important_my:
            second = (
                ungettext("%d my task", "%d my tasks", num_important_my)
                % num_important_my
            )
            return mark_safe(u"{} <b>({})</b>".format(first, second))
        return first
    return ""


@register.inclusion_tag('inc_competition_chain_ctask_tr.html', takes_context=True)
def chain_ctask_tr(context, ctask, counter=None, total_ctasks=None):
    return {
        'competition': context['competition'],
        'ctask': ctask,
        'counter': counter,
        'total_ctasks': total_ctasks,
    }


@register.simple_tag(takes_context=False)
def chain_list_ctask_name_text(ctask, truncate):
    truncated = truncatechars(ctask.task.content.text or '', truncate)
    if ctask.competition.use_custom_ctask_names():
        return mark_safe(
            u"<b>{}:</b> {}".format(xss.escape(ctask.task.name), xss.escape(truncated))
        )
    else:
        return truncated


CHAIN_LIST_CTASK_COMMENT_PREVIEW_RE = re.compile(r'\s*\[\s*hide\s*\]')


@register.simple_tag(takes_context=False)
def chain_list_ctask_comment_preview(ctask):
    truncate = 40 if ctask.chain_id else 30
    truncated = truncatechars(ctask.comment.text or '', truncate)
    search = CHAIN_LIST_CTASK_COMMENT_PREVIEW_RE.search(truncated)
    return truncated[: search.start()] + '...' if search else truncated


@register.simple_tag(takes_context=True)
def chain_class(context, chain):
    cls = 'comp-chain'
    if chain.t_is_locked and context['has_started']:
        cls += ' comp-chain-locked'
    if chain.t_next_task is not None:
        cls += ' comp-chain-unfinished'
    return cls


@register.simple_tag(takes_context=True)
def admin_chain_class(context, chain):
    num_important, num_important_my = parse_chain_comments_cache(chain, context['user'])
    if num_important_my > 0:
        return 'cchain-important-my-ctasks'
    elif num_important > 0:
        return 'cchain-important'
    elif chain.t_is_verified:
        return 'cchain-verified'
    return ''


@register.simple_tag(takes_context=True)
def ctask_comment_class(context, ctask):
    return utils__ctask_comment_class(ctask, context['user'])


@register.simple_tag()
def ctask_score_text(ctask):
    text = (
        ungettext(
            "This task is worth %d point.",
            "This task is worth %d points.",
            ctask.max_score,
        )
        % ctask.max_score
    )
    return u'<div class="ctask-score-text">{}</div>'.format(text)


@register.simple_tag()
def chain_badge_class(chain):
    if all(ctask.t_is_solved for ctask in chain.ctasks):
        return "badge-success"
    if any(ctask.t_submission_count > ctask.max_submissions for ctask in chain.ctasks):
        return ""
    return "badge-info"


@register.simple_tag()
def legend_ctask(_class, text):
    return mark_safe(
        u'<tr>'
        u'<td width="100%">'
        u'<div class="progress"><div class="{}"></div></div>'
        u'</td>'
        u'<td>{}</td>'
        u'</tr>'.format(_class, text)
    )


@register.simple_tag()
def legend_chain(_class, text):
    return mark_safe(
        u'<tr>'
        u'<td width="100%"><span class="badge {}">+1</span></td>'
        u'<td>{}</td>'
        u'</tr>'.format(_class, text)
    )


@register.simple_tag(takes_context=True)
def send_notification_link(context, team_id=None, ctask_id=None):
    params = {}
    if team_id:
        params['team'] = team_id
    if ctask_id:
        params['ctask'] = ctask_id
    end = '?{}#post'.format(urllib.urlencode(params))
    url = utils__comp_url(context['competition'], 'notifications/admin') + end
    return mark_safe(u'<a href="{}"><i class="icon-envelope"></i></a>'.format(url))


@register.simple_tag(takes_context=True)
def team_score(context, team):
    """Outputs formatted team score.

    Takes into account if the scoreboard is frozen, were there any submissions
    after the freeze, is the current user a member of the given team or if it
    is a competition admin.
    """
    result = str(team.cache_score_before_freeze)
    if context['is_scoreboard_frozen']:
        before = team.cache_score_before_freeze
        max_after = team.cache_max_score_after_freeze
        if before != max_after:
            result += " (+{}?)".format(max_after - before)
            if context['team'] == team or context['is_admin']:
                result += " ({})".format(team.cache_score)
    return result


def _action_message(action):
    if action.type_pair == _action.COMPETITION_UPDATE_SUBMISSION_SCORE:
        # action_object_id is used in a hacky way to store the score.
        score = action.action_object_id
        msg = (
            ungettext(
                "%(actor)s updated the score to %(score)d.",
                "%(actor)s updated the score to %(score)d.",
                score,
            )
            % {'score': score, 'actor': userlink(action.actor)}
        )
    else:
        msg = u"Unknown action {}!".format(action)
    return mark_safe(msg)


def get_submission_actions(submission):
    content_type_id = ContentType.objects.get_for_model(Submission).id
    actions = list(
        Action.objects.filter(
            target_content_type_id=content_type_id, target_id=submission.id
        )
        .exclude(type=_action.POST_SEND[0])
        .select_related('actor')
    )
    not_graded = all(
        action.type_pair != _action.COMPETITION_UPDATE_SUBMISSION_SCORE
        for action in actions
    )
    return actions, not_graded


@register.inclusion_tag('inc_competition_submission_posts.html', takes_context=True)
def show_submission_posts(context, submission, unread_newer_than, actions=None):
    posts = list(
        submission.posts.select_related('author', 'content', 'last_edit_by').order_by(
            '-date_created'
        )
    )
    user = context['user']
    for x in posts:
        x.cache_can_edit = x.can_edit(user, submission)
        if (
            unread_newer_than
            and x.last_edit_time >= unread_newer_than
            and x.last_edit_by_id != context['user'].id
        ):
            x.t_unread = True
        x.t_is_post = True

    if not actions:
        actions, not_graded = get_submission_actions(submission)
    for action in actions:
        if unread_newer_than and action.date_created >= unread_newer_than:
            action.t_unread = True
        action.t_message = _action_message(action)

    events = actions + posts
    events.sort(key=lambda x: x.date_created, reverse=True)

    return {
        'events': events,
        'submission': submission,
        'request': context['request'],
        'user': user,
    }


@register.inclusion_tag('inc_competition_solution_format.html', takes_context=True)
def show_solution_format_instructions(context):
    """Used optionally by the competition-specific rules HTML files."""
    return context
