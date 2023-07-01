from __future__ import print_function

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from django.contrib.contenttypes.models import ContentType
from django.db import connection, transaction
from django.db.models import Count, F
from django.db.models.signals import post_save
from django.dispatch import receiver

from skoljka.competition.evaluator import (
    InvalidDescriptor,
    InvalidSolution,
    get_evaluator,
)
from skoljka.competition.models import (
    Chain,
    Competition,
    CompetitionTask,
    Submission,
    Team,
    TeamMember,
)
from skoljka.post.models import Post


def comp_url(competition, url_suffix):
    # TODO: Do it the proper way. Use names, not suffices.
    suffix = '/' if url_suffix else ''
    return competition.get_absolute_url() + url_suffix + suffix


# TODO(ivica): Add commit argument to all update_* methods.
def update_ctask_task(task, competition, chain, position, name, commit=False):
    """Updates task.name and .source. Does not save!"""
    if not name:
        if chain is None:
            name = u"{} - (no chain)".format(competition.name)
        else:
            name = u"{} - {} #{}".format(competition.name, chain.name, position)
    task.name = name
    task.source = competition.name
    if commit:
        task.save()


_is_important_re = re.compile(r'^IMPORTANT:', re.MULTILINE)


def is_ctask_comment_important(comment):
    return bool(_is_important_re.search(comment))


def update_chain_comments_cache(chain, ctasks, commit=False):
    count_by_author = defaultdict(int)
    for ctask in ctasks:
        if is_ctask_comment_important(ctask.comment.text):
            count_by_author[ctask.task.author_id] += 1
    chain.cache_ctask_comments_info = ','.join(
        ['{}:{}'.format(author_id, cnt) for author_id, cnt in count_by_author.items()]
    )
    if commit:
        chain.save()


def parse_chain_comments_cache(chain, current_user):
    """Returns num_important, num_important_my."""
    cache = chain.cache_ctask_comments_info
    num_important = 0
    num_important_my = 0
    if cache:
        for author_cnt in cache.split(','):
            author_id, count = [int(x) for x in author_cnt.split(':')]
            num_important += count
            if author_id == current_user.id:
                num_important_my = count
    return num_important, num_important_my


def ctask_comment_class(ctask, current_user, is_important=None):
    """is_important --> boolean True/False or None if not checked yet
    (micro-optimization)."""
    if (
        is_important is None
        and is_ctask_comment_important(ctask.comment.text)
        or is_important
    ):
        if ctask.task.author_id == current_user.id:
            return 'ctask-comment-important ctask-my'
        return 'ctask-comment-important'
    return ''


def ctask_comment_verified_class(competition, ctask, current_task, is_important=None):
    result = ctask_comment_class(ctask, current_task, is_important)
    if result:
        return result
    if ctask.cache_admin_solved_count >= competition.min_admin_solved_count:
        return 'ctask-verified'
    return ''


def _compute_chain_score(chain_bonus, ctask_infos, submission_infos):
    """Compute total score for a given chain.

    The chain bonus is applied only if for each ctasks there is a full score
    submission.

    Arguments:
        chain_bonus: int
        ctask_infos: list of pairs (ctask_id, max_score)
        submission_infos: list of pairs (ctask_id, score)
    """
    best = {}
    for ctask_id, score in submission_infos:
        best[ctask_id] = max(best.get(ctask_id, 0), score)

    total = sum(best.values())
    if all(best.get(ctask_id) == max_score for ctask_id, max_score in ctask_infos):
        total += chain_bonus
    return total


def compute_chain_score_variants(competition, chain, chain_ctasks, chain_submissions):
    """Compute three variants of score for a given chain:
    - the actual score
    - the score before the freeze
    - the maximum theoretical score after the freeze.
    """
    freeze_date = competition.scoreboard_freeze_date
    ctask_infos = [(ctask.id, ctask.max_score) for ctask in chain_ctasks]
    max_ctask_scores = dict(ctask_infos)

    # True score.
    infos = [(x.ctask_id, x.score) for x in chain_submissions]
    score0 = _compute_chain_score(chain.bonus_score, ctask_infos, infos)

    # Score before freeze.
    infos = [(x.ctask_id, x.score) for x in chain_submissions if x.date <= freeze_date]
    score1 = _compute_chain_score(chain.bonus_score, ctask_infos, infos)

    # Max score after freeze.
    infos = [
        (x.ctask_id, max_ctask_scores[x.ctask_id])
        if x.date > freeze_date
        else (x.ctask_id, x.score)
        for x in chain_submissions
    ]
    score2 = _compute_chain_score(chain.bonus_score, ctask_infos, infos)

    return score0, score1, score2


def update_score_on_ctask_action(
    competition, team, chain, chain_ctasks, old_chain_submissions, new_chain_submissions
):
    """Updates team score after one or more submissions have been updated."""

    old = compute_chain_score_variants(
        competition, chain, chain_ctasks, old_chain_submissions
    )
    new = compute_chain_score_variants(
        competition, chain, chain_ctasks, new_chain_submissions
    )

    if old != new:
        team.cache_score += new[0] - old[0]
        team.cache_score_before_freeze += new[1] - old[1]
        team.cache_max_score_after_freeze += new[2] - old[2]
        team.save()


def refresh_teams_cache_score(teams):
    # TODO: Atomic.
    teams = list(teams)
    if not teams:
        return

    competition_ids = list(set(team.competition_id for team in teams))
    teams = {team.id: team for team in teams}

    competitions_dict = Competition.objects.in_bulk(competition_ids)
    all_ctasks = CompetitionTask.objects.filter(competition_id__in=competition_ids)
    all_submissions = list(
        Submission.objects.filter(team_id__in=teams.keys()).only(
            'team', 'ctask', 'date', 'score'
        )
    )

    chain_ctasks = defaultdict(list)
    ctasks_chain = {}
    for ctask in all_ctasks:
        chain_ctasks[ctask.chain_id].append(ctask)
        ctasks_chain[ctask.id] = ctask.chain_id

    team_chain_submissions = {team_id: defaultdict(list) for team_id in teams.keys()}
    for submission in all_submissions:
        chain_id = ctasks_chain[submission.ctask_id]
        team_chain_submissions[submission.team_id][chain_id].append(submission)

    chains_dict = Chain.objects.in_bulk(list(chain_ctasks.keys()))

    queries_args = []
    for team_id, chain_submissions in team_chain_submissions.items():
        S0, S1, S2 = 0, 0, 0
        for chain_id, chain_sub in chain_submissions.items():
            if chain_id is None:
                continue
            chain = chains_dict[chain_id]
            s0, s1, s2 = compute_chain_score_variants(
                competitions_dict[chain.competition_id],
                chain,
                chain_ctasks[chain_id],
                chain_sub,
            )
            S0 += s0
            S1 += s1
            S2 += s2

        team = teams[team_id]
        team.cache_score = S0
        team.cache_score_before_freeze = S1
        team.cache_max_score_after_freeze = S2
        queries_args.append((S0, S1, S2, int(team_id)))
    cursor = connection.cursor()
    cursor.executemany(
        'UPDATE `competition_team` SET `cache_score`=%s, '
        '`cache_score_before_freeze`=%s, `cache_max_score_after_freeze`=%s '
        'WHERE `id`=%s;',
        queries_args,
    )
    transaction.commit_unless_managed()


def lock_ctasks_in_chain(chain, ctasks):
    locked = False
    for ctask in ctasks:
        ctask.t_is_locked = locked and not ctask.t_is_partially_solved
        if (
            chain
            and chain.unlock_mode == Chain.UNLOCK_GRADUAL
            and not ctask.t_is_partially_solved
            and ctask.t_submission_count < ctask.max_submissions
        ):
            locked = True


def load_and_preprocess_chain(competition, chain, team, preloaded_ctask=None):
    ctasks = list(
        CompetitionTask.objects.filter(chain=chain)
        .order_by('chain_position', 'id')
        .only('id', 'max_submissions')
    )
    if preloaded_ctask:
        ctasks = [
            preloaded_ctask if ctask.id == preloaded_ctask.id else ctask
            for ctask in ctasks
        ]

    ctask_ids = [ctask.id for ctask in ctasks]
    submissions = list(Submission.objects.filter(ctask_id__in=ctask_ids, team=team))

    preprocess_chain(competition, chain, ctasks, submissions)
    return ctasks, submissions


def preprocess_chain(competition, chain, ctasks, submissions):
    """

    Note: ctasks must be sorted by chain position!
    """
    prev_ctask = None
    for ctask in ctasks:
        ctask.t_submission_count = 0
        ctask.t_is_partially_solved = False
        ctask.t_is_solved = False
        if competition:
            ctask.competition = competition
        if prev_ctask:
            prev_ctask.t_next = ctask
        prev_ctask = ctask
    if prev_ctask is not None:
        prev_ctask.t_next = None

    ctasks_dict = {ctask.id: ctask for ctask in ctasks}
    for submission in submissions:
        ctask = ctasks_dict[submission.ctask_id]
        ctask.t_submission_count += 1
        ctask.t_is_partially_solved |= submission.score > 0
        ctask.t_is_solved |= submission.score == ctask.max_score

    lock_ctasks_in_chain(chain, ctasks)


def refresh_submissions_score(submissions=None, ctasks=None, competitions=None):
    """Refresh submissions cores for automatically graded tasks.

    Returns the number of solutions updated."""
    if not submissions and not ctasks and not competitions:
        raise ValueError
    # TODO: simplify this
    if competitions:
        id_to_comp = {x.id: x for x in competitions}
        if ctasks is None:
            ctasks = CompetitionTask.objects.filter(
                competition_id__in=id_to_comp.keys()
            )
            for ctask in ctasks:
                ctask.competition = id_to_comp[ctask.competition_id]
        # TODO: select only given ctasks
        if submissions is None:
            submissions = Submission.objects.filter(
                ctask__competition_id__in=id_to_comp.keys()
            )
    elif ctasks is None:
        # TODO: get submissions if not provided.
        ctask_ids = set(submission.ctask_id for submission in submissions)
        ctasks = CompetitionTask.objects.filter(id__in=ctask_ids).select_related(
            'competition__evaluator_version'
        )

    ctasks = list(ctasks)
    ctasks_dict = {ctask.id: ctask for ctask in ctasks}

    updated = 0
    for submission in submissions:
        ctask = ctasks_dict[submission.ctask_id]
        if not ctask.is_automatically_graded():
            continue
        evaluator = get_evaluator(ctask.competition.evaluator_version)
        old = submission.score
        try:
            new = evaluator.check_result(ctask.descriptor, submission.result)
            new *= ctask.max_score
        except (InvalidSolution, InvalidDescriptor):
            new = 0
        if old != new:
            submission.score = new
            submission.save()
            updated += 1
    return updated


def get_teams_for_user_ids(competition, user_ids):
    team_members = list(
        TeamMember.objects.filter(
            team__competition_id=competition.id, member_id__in=set(user_ids)
        )
        .select_related('team')
        .only('member', 'team')
    )

    return {x.member_id: x.team for x in team_members}


def get_ctask_statistics(competition_id):
    """
    # TODO: documentation
    """
    # TODO: cache!
    ctask_infos = list(
        CompetitionTask.objects.filter(competition_id=competition_id).values_list(
            'id', 'max_submissions', 'max_score'
        )
    )
    max_submissions_dict = {ctask_id: sub for ctask_id, sub, max_score in ctask_infos}
    max_scores_dict = {ctask_id: max_score for ctask_id, sub, max_score in ctask_infos}
    team_types = dict(
        Team.objects.filter(competition_id=competition_id).values_list(
            'id', 'team_type'
        )
    )
    submissions = Submission.objects.filter(
        ctask__competition_id=competition_id
    ).values_list('team_id', 'ctask_id', 'score')

    submission_count_dict = defaultdict(int)
    is_solved_dict = defaultdict(bool)
    for team_id, ctask_id, score in submissions:
        key = (team_id, ctask_id)
        submission_count_dict[key] += 1
        is_solved_dict[key] |= score == max_scores_dict[ctask_id]

    result = defaultdict(int)
    for key, submission_count in submission_count_dict.iteritems():
        is_solved = is_solved_dict[key]
        team_type = team_types[key[0]]

        if is_solved:
            _key = 'S'  # solved
        elif submission_count >= max_submissions_dict[key[1]]:
            _key = 'F'  # failed
        else:
            _key = 'T'  # tried

        _key = str(int(team_type)) + _key + str(key[1])
        result[_key] += 1

    return result


def detach_ctask_from_chain(ctask):
    CompetitionTask.objects.filter(
        chain_id=ctask.chain_id, chain_position__gt=ctask.chain_position
    ).update(chain_position=F('chain_position') - 1)
    ctask.chain_id = None
    ctask.chain_position = -1
    ctask.save()


def delete_chain(chain):
    CompetitionTask.objects.filter(chain=chain).update(chain=None, chain_position=-1)
    chain.delete()


def update_chain_ctasks(competition, chain, old_ids, new_ids):
    # TODO: Update .task name.
    queries_args = []
    for ctask_id in set(old_ids) - set(new_ids):
        queries_args.append(("NULL", -1, ctask_id))
    for k, ctask_id in enumerate(new_ids, 1):
        queries_args.append((chain.id, k, ctask_id))

    if queries_args:
        cursor = connection.cursor()
        cursor.executemany(
            'UPDATE `competition_competitiontask` '
            'SET `chain_id`=%s, `chain_position`=%s '
            'WHERE `id`=%s;',
            queries_args,
        )
        transaction.commit_unless_managed()

    ctasks = CompetitionTask.objects.filter(id__in=new_ids).select_related(
        'comment', 'task'
    )
    update_chain_comments_cache(chain, ctasks)
    update_chain_cache_is_verified(competition, chain)


def refresh_chain_cache_is_verified(competition):
    """Refresh cache_is_verified for all chains in the given competition.
    Returns the list of IDs of the updated chains."""
    # TODO: Atomic.
    chains_was_verified = list(
        Chain.objects.filter(competition=competition).values_list(
            'id', 'cache_is_verified'
        )
    )
    ctasks = list(
        CompetitionTask.objects.filter(competition=competition).values_list(
            'id', 'chain_id', 'cache_admin_solved_count'
        )
    )

    not_verified = set()
    for ctask_id, chain_id, solved_count in ctasks:
        if chain_id is not None and solved_count < competition.min_admin_solved_count:
            not_verified.add(chain_id)

    queries_args = []
    for chain_id, was_verified in chains_was_verified:
        verified = chain_id not in not_verified
        if was_verified != verified:
            queries_args.append((int(verified), chain_id))

    if queries_args:
        cursor = connection.cursor()
        cursor.executemany(
            'UPDATE `competition_chain` SET `cache_is_verified`=%s WHERE `id`=%s;',
            queries_args,
        )
        transaction.commit_unless_managed()

    return [x[1] for x in queries_args]  # Extract IDs.


def update_chain_cache_is_verified(competition, chain):
    """Update cache_is_verified for the given chain."""
    verified = not CompetitionTask.objects.filter(
        chain=chain, cache_admin_solved_count__lt=competition.min_admin_solved_count
    ).exists()
    if chain.cache_is_verified != verified:
        chain.cache_is_verified = verified
        Chain.objects.filter(id=chain.id).update(cache_is_verified=verified)


def refresh_ctask_cache_admin_solved_count(competition):
    """Refresh cache_admin_solved_count for all ctasks in the given competition.
    Returns the list of IDs of the updated ctasks.
    DOES NOT update chain.cache_is_verified!"""
    # TODO: Atomic.
    ctasks_old_count = list(
        CompetitionTask.objects.filter(competition=competition).values_list(
            'id', 'cache_admin_solved_count'
        )
    )

    # Not sure why we need `id` here, but for some reason it doesn't return all
    # the rows otherwise. (ivica)
    verified_ctask_ids = set(
        Submission.objects.filter(
            team__competition_id=competition.id,
            team__team_type=Team.TYPE_ADMIN_PRIVATE,
            score=F('ctask__max_score'),
        )
        .exclude(team__author=F('ctask__task__author'))
        .values_list('id', 'ctask_id')
    )

    solved_count = Counter()
    for submission_id, ctask_id in verified_ctask_ids:
        solved_count[ctask_id] += 1

    queries_args = []
    for ctask_id, old_count in ctasks_old_count:
        count = solved_count[ctask_id]
        if count != old_count:
            queries_args.append((count, ctask_id))

    if queries_args:
        cursor = connection.cursor()
        cursor.executemany(
            'UPDATE `competition_competitiontask` SET '
            '`cache_admin_solved_count`=%s WHERE `id`=%s;',
            queries_args,
        )
        transaction.commit_unless_managed()

    return [x[1] for x in queries_args]  # Extract IDs.


def update_ctask_cache_admin_solved_count(competition, ctask, chain):
    """Update cache_admin_solved_count for the given ctask.
    Also takes care of chain.cache_is_verified."""
    solved_count = (
        Submission.objects.filter(
            ctask_id=ctask.id,
            team__competition_id=competition.id,
            team__team_type=Team.TYPE_ADMIN_PRIVATE,
            score=F('ctask__max_score'),
        )
        .exclude(team__author=F('ctask__task__author'))
        .count()
    )
    min_solved_count = competition.min_admin_solved_count

    before = ctask.cache_admin_solved_count >= min_solved_count
    ctask.cache_admin_solved_count = solved_count
    ctask.save()
    after = ctask.cache_admin_solved_count >= min_solved_count

    if before != after and chain is not None:
        update_chain_cache_is_verified(competition, chain)


@transaction.commit_on_success
def refresh_ctask_cache_new_activities_count(competition):
    """Refresh cache_new_activities_count for all ctasks of a given competition.
    Returns the list of IDs of the updated ctasks."""
    old = dict(
        CompetitionTask.objects.select_for_update()
        .filter(competition_id=competition.id)
        .values_list('id', 'cache_new_activities_count')
    )
    new = dict(
        CompetitionTask.objects.filter(competition_id=competition.id)
        .values('id')
        .filter(
            submission__oldest_unseen_team_activity__gt=Submission.NO_UNSEEN_ACTIVITIES_DATETIME
        )
        .annotate(new_count=Count('submission'))
        .values_list('id', 'new_count')
    )

    args = []
    for id in set(new.keys()) | set(old.keys()):
        new_cnt = new.get(id, 0)
        if new_cnt != old.get(id, 0):
            args.append((new_cnt, id))
    if args:
        connection.cursor().executemany(
            'UPDATE `competition_competitiontask` '
            'SET `cache_new_activities_count`=%s '
            'WHERE `id`=%s;',
            args,
        )

    ids = [id for new_cnt, id in args]
    return ids


def parse_team_categories(team_categories, lang):
    """Parse `competition.team_categories` formatted string.

    New format (JSON):
        '{"lang": {"ID1": "name", ...}, ...}'
    Old format:
        "ID1: name | ..."

    Returns a list `[(id, name), ...]`, where `id` is an `int`.

    Raises ValueError, KeyError or TypeError if the format is invalid."""
    if not team_categories.startswith('{'):
        return _parse_team_categories_old(team_categories)

    parsed = json.loads(team_categories)
    categories = parsed[lang]
    out = [(int(id), name) for id, name in categories.items()]
    out.sort(key=lambda f: f[0])
    return out


def _parse_team_categories_old(team_categories):
    # Format is "ID1:name1 | ID2:name2 | ...", where the last item is
    # considered the default.
    categories = []
    for category in team_categories.split('|'):
        if not category.strip():
            continue
        category = category.split(':')
        if len(category) != 2:
            raise ValueError("Invalid format of team_categories!")
        ID = int(category[0])  # Might raise a ValueError.
        name = category[1].strip()
        categories.append((ID, name))
    return categories


@receiver(post_save, sender=Post)
def _mark_submission_as_unseen(sender, instance, **kwargs):
    """Mark the submission as unseen, either to the team if the post was
    admin's or to the admin if the post was team's."""
    submission_content_type = ContentType.objects.get_for_model(Submission)
    if instance.content_type_id == submission_content_type.id:
        submission = instance.content_object
        if submission.ctask.competition.is_user_admin(instance.last_edit_by):
            if submission.mark_unseen_admin_activity():
                submission.save()
        else:
            if submission.mark_unseen_team_activity():
                submission.save()
