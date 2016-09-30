from django.db import connection, transaction
from django.db.models import F

from competition.models import Chain, Competition, CompetitionTask, \
        Submission, Team, TeamMember
from competition.evaluator import get_evaluator, InvalidSolution, \
        InvalidDescriptor

from collections import Counter, defaultdict
from datetime import timedelta

import re

def comp_url(competition, url_suffix):
    # TODO: Do it the proper way. Use names, not suffices.
    suffix = '/' if url_suffix else ''
    return competition.get_absolute_url() + url_suffix + suffix


# TODO(ivica): Add commit argument to all update_* methods.
def update_ctask_task(task, competition, chain, position, commit=False):
    """Updates task.name and .source. Does not save!"""
    if chain is None:
        name = u"{} - (no chain)".format(competition.name)
    else:
        name = u"{} - {} #{}".format(competition.name, chain.name, position)
    task.name = name
    task.source = competition.name
    if commit:
        task.save()


def fix_ctask_order(competition, chain, ctasks):
    """Fix ctask chain_position if not correctly set.

    Method checks if chain positions are consecutive, unique and start from 1.
    If not, the chain positions are fixed and an appropriate comment is added
    to each of the tasks affected.

    Returns True if any changes were made.
    """
    changes = False

    for k, ctask in enumerate(ctasks, 1):
        if ctask.chain_position != k:
            changes = True
            ctask.chain_position = k
            update_ctask_task(ctask.task, competition, chain, k, commit=True)
            ctask.comment.text += "\nIMPORTANT: Please check whether the " \
                                  "tasks are in the right order! (automatic)"
            ctask.comment.html = None
            ctask.comment.save()
            ctask.save()
    if changes:
        update_chain_comments_cache(chain, ctasks, commit=True)
    return changes


_is_important_re = re.compile(r'^IMPORTANT:', re.MULTILINE)
def is_ctask_comment_important(comment):
    return bool(_is_important_re.search(comment))


def update_chain_comments_cache(chain, ctasks, commit=False):
    count_by_author = defaultdict(int)
    for ctask in ctasks:
        if is_ctask_comment_important(ctask.comment.text):
            count_by_author[ctask.task.author_id] += 1
    chain.cache_ctask_comments_info = ','.join(
            ['{}:{}'.format(author_id, cnt) \
                    for author_id, cnt in count_by_author.items()])
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
    if is_important is None and is_ctask_comment_important(ctask.comment.text) \
            or is_important:
        if ctask.task.author_id == current_user.id:
            return 'ctask-comment-important ctask-my'
        return 'ctask-comment-important'
    return ''


def ctask_comment_verified_class(competition, ctask, current_task,
        is_important=None):
    result = ctask_comment_class(ctask, current_task, is_important)
    if result:
        return result
    if ctask.cache_admin_solved_count >= competition.min_admin_solved_count:
        return 'ctask-verified'
    return ''


def update_score_on_ctask_action(competition, team, chain, ctask, submission,
        delete, chain_ctask_ids=None, chain_submissions=None):
    """Updates team score for a given submit/delete action."""
    if not submission:
        return
    if chain_ctask_ids is None:
        chain_ctask_ids = CompetitionTask.objects \
                .filter(chain=chain).values_list('id', flat=True)
    if chain_submissions is None:
        chain_submissions = Submission.objects.filter(
                team=team, ctask_id__in=chain_ctask_ids)

    save = [False]  # Inner method will be able to edit save[0].
    def _calc_score_delta(should_count_func):
        _should_count_submission = should_count_func(submission)
        if not _should_count_submission:
            return 0
        _potential_solutions_count = defaultdict(int)
        for _submission in chain_submissions:
            if should_count_func(_submission):
                _potential_solutions_count[_submission.ctask_id] += 1

        if not delete and _potential_solutions_count.get(ctask.id) == 1:
            _delta = ctask.score
            if len(_potential_solutions_count) == len(chain_ctask_ids):
                _delta += chain.bonus_score
        elif delete and ctask.id not in _potential_solutions_count:
            _delta = -ctask.score
            if len(_potential_solutions_count) == len(chain_ctask_ids) - 1:
                _delta -= chain.bonus_score
        else:
            return 0

        save[0] = True
        return _delta

    freeze_date = competition.scoreboard_freeze_date
    team.cache_score += _calc_score_delta(lambda x: x.cache_is_correct)
    team.cache_score_before_freeze += _calc_score_delta(
            lambda x: x.cache_is_correct and x.date <= freeze_date)
    team.cache_max_score_after_freeze += _calc_score_delta(
            lambda x: x.cache_is_correct or x.date > freeze_date)

    if save[0]:
        team.save()


def refresh_teams_cache_score(teams):
    # TODO: Atomic.
    teams = list(teams)
    if not teams:
        return

    team_ids = [team.id for team in teams]
    competition_ids = list(set([team.competition_id for team in teams]))

    all_competitions = list(Competition.objects.filter(id__in=competition_ids))
    all_ctasks = list(CompetitionTask.objects.filter(
            competition_id__in=competition_ids))
    all_chains = list(Chain.objects.filter(competition_id__in=competition_ids))
    all_submissions = list(Submission.objects \
            .filter(team_id__in=team_ids) \
            .values_list('team_id', 'ctask_id', 'date', 'cache_is_correct'))

    competitions_dict = {comp.id: comp for comp in all_competitions}
    ctasks_dict = {ctask.id: ctask for ctask in all_ctasks}
    chains_dict = {chain.id: chain for chain in all_chains}
    chains_by_comp = defaultdict(list)
    ctasks_by_chain = defaultdict(list)

    for chain in all_chains:
        chains_by_comp[chain.competition_id].append(chain)
    for ctask in all_ctasks:
        ctasks_by_chain[ctask.chain_id].append(ctask)

    def _calculate_score(is_solved):
        """is_solved is a list/set of pairs (team_id, ctask_id)."""
        is_solved = set(is_solved)
        teams_score = {}
        for team in teams:
            score = 0
            for chain in chains_by_comp[team.competition_id]:
                all_solved = True
                for ctask in ctasks_by_chain[chain.id]:
                    if (team.id, ctask.id) in is_solved:
                        score += ctask.score
                    else:
                        all_solved = False
                if all_solved:
                    score += chain.bonus_score
            teams_score[team.id] = score
        return teams_score

    submissions_correct = []
    submissions_correct_before = []
    submissions_correct_or_after = []
    for submission in all_submissions:
        pair = (submission[0], submission[1])  # team_id, ctask_id
        ctask = ctasks_dict[submission[1]]     # ctask_id
        competition = competitions_dict[ctask.competition_id]
        if submission[3]:                      # cache_is_correct
            submissions_correct.append(pair)
            if submission[2] <= competition.scoreboard_freeze_date:  # date
                submissions_correct_before.append(pair)
        if submission[3] or submission[2] > competition.scoreboard_freeze_date:
            submissions_correct_or_after.append(pair)
    score_before = _calculate_score(submissions_correct_before)
    score_all = _calculate_score(submissions_correct)
    score_max = _calculate_score(submissions_correct_or_after)

    queries_args = []
    for team in teams:
        team.cache_score = score_all.get(team.id, 0)
        team.cache_score_before_freeze = score_before.get(team.id, 0)
        team.cache_max_score_after_freeze = score_max.get(team.id, 0)
        queries_args.append((team.cache_score, team.cache_score_before_freeze,
                team.cache_max_score_after_freeze, int(team.id)))
    cursor = connection.cursor()
    cursor.executemany(
            "UPDATE `competition_team` SET `cache_score`=%s, "
            "`cache_score_before_freeze`=%s, `cache_max_score_after_freeze`=%s "
            "WHERE `id`=%s;", queries_args)
    transaction.commit_unless_managed()


def lock_ctasks_in_chain(ctasks):
    locked = False
    for ctask in ctasks:
        ctask.t_is_locked = locked and not ctask.t_is_solved
        if not ctask.t_is_solved \
                and ctask.t_submission_count < ctask.max_submissions:
            locked = True


def preprocess_chain(competition, chain, team, preloaded_ctask=None):
    ctasks = list(CompetitionTask.objects.filter(chain=chain) \
            .order_by('chain_position', 'id') \
            .only('id', 'max_submissions'))
    if preloaded_ctask:
        ctasks = [preloaded_ctask if ctask.id == preloaded_ctask.id else ctask \
                for ctask in ctasks]

    ctasks_dict = {ctask.id: ctask for ctask in ctasks}
    submissions = list(Submission.objects \
            .filter(ctask_id__in=ctasks_dict.keys(), team=team))

    prev_ctask = None
    for ctask in ctasks:
        ctask.t_submission_count = 0
        ctask.t_is_solved = False
        if competition:
            ctask.competition = competition
        if prev_ctask:
            prev_ctask.t_next = ctask
        prev_ctask = ctask
    ctask.t_next = None

    for submission in submissions:
        ctask = ctasks_dict[submission.ctask_id]
        ctask.t_submission_count += 1
        ctask.t_is_solved |= submission.cache_is_correct

    lock_ctasks_in_chain(ctasks)

    return ctasks, submissions


def refresh_submissions_cache_is_correct(submissions=None, ctasks=None,
        competitions=None):
    """Returns the number of solutions updated."""
    if not submissions and not ctasks and not competitions:
        raise ValueError
    # TODO: simplify this
    if competitions:
        competitions = list(competitions)
        id_to_comp = {x.id: x for x in competitions}
        if ctasks is None:
            ctasks = CompetitionTask.objects \
                    .filter(competition_id__in=id_to_comp.keys())
            for ctask in ctasks:
                ctask.competition = id_to_comp[ctask.competition_id]
        # TODO: select only given ctasks
        if submissions is None:
            submissions = Submission.objects \
                    .filter(ctask__competition_id__in=id_to_comp.keys())
    elif ctasks is None:
        # TODO: get submissions if not provided.
        ctask_ids = set(submission.ctask_id for submission in submissions)
        ctasks = CompetitionTask.objects.filter(id__in=ctask_ids) \
                .select_related('competition__evaluator_version')

    ctasks = list(ctasks)
    ctasks_dict = {ctask.id: ctask for ctask in ctasks}

    updated = 0
    for submission in submissions:
        ctask = ctasks_dict[submission.ctask_id]
        evaluator = get_evaluator(ctask.competition.evaluator_version)
        old = submission.cache_is_correct
        try:
            new = evaluator.check_result(ctask.descriptor, submission.result)
        except InvalidSolution, InvalidDescriptor:
            new = False
        if old != new:
            submission.cache_is_correct = new
            submission.save()
            updated += 1
    return updated


def get_teams_for_user_ids(user_ids):
    team_members = list(TeamMember.objects.filter(member_id__in=set(user_ids)) \
            .select_related('team') \
            .only('member', 'team'))

    return {x.member_id: x.team for x in team_members}


def get_ctask_statistics(competition_id):
    """
    # TODO: documentation
    """
    # TODO: cache!
    max_submissions_dict = dict(CompetitionTask.objects \
            .filter(competition_id=competition_id) \
            .values_list('id', 'max_submissions'))
    team_types = dict(Team.objects \
            .filter(competition_id=competition_id) \
            .values_list('id', 'team_type'))
    submissions = Submission.objects \
            .filter(ctask__competition_id=competition_id) \
            .values_list('team_id', 'ctask_id', 'cache_is_correct')

    submission_count_dict = defaultdict(int)
    is_solved_dict = defaultdict(bool)
    for team_id, ctask_id, cache_is_correct in submissions:
        key = (team_id, ctask_id)
        submission_count_dict[key] += 1
        is_solved_dict[key] |= cache_is_correct

    result = defaultdict(int)
    for key, submission_count in submission_count_dict.iteritems():
        is_solved = is_solved_dict[key]
        team_type = team_types[key[0]]

        if is_solved:
            _key = 'S' # solved
        elif submission_count >= max_submissions_dict[key[1]]:
            _key = 'F' # failed
        else:
            _key = 'T' # tried

        _key = str(int(team_type)) + _key + str(key[1])
        result[_key] += 1

    return result


def detach_ctask_from_chain(ctask):
    CompetitionTask.objects \
            .filter(chain_id=ctask.chain_id,
                    chain_position__gt=ctask.chain_position) \
            .update(chain_position=F('chain_position') - 1)
    ctask.chain_id = None
    ctask.chain_position = -1
    ctask.save()


def delete_chain(chain):
    CompetitionTask.objects.filter(chain=chain).update(
            chain=None, chain_position=-1)
    chain.delete()


def update_chain_ctasks(competition, chain, old_ids, new_ids):
    # TODO: Update .task name.
    queries_args = []
    for ctask_id in set(old_ids) - set(new_ids):
        queries_args.append(("NULL", -1, ctask_id))
    for k, ctask_id in enumerate(new_ids, 1):
        queries_args.append((chain.id, k, ctask_id))

    print 'OLD NEW_IDS', old_ids, new_ids
    print 'QUERIES', queries_args
    if queries_args:
        cursor = connection.cursor()
        cursor.executemany(
                "UPDATE `competition_competitiontask` "
                "SET `chain_id`=%s, `chain_position`=%s "
                "WHERE `id`=%s;", queries_args)
        transaction.commit_unless_managed()

    ctasks = CompetitionTask.objects.filter(id__in=new_ids) \
            .select_related('comment', 'task')
    update_chain_comments_cache(chain, ctasks)
    update_chain_cache_is_verified(competition, chain)


def refresh_chain_cache_is_verified(competition):
    """Refresh cache_is_verified for all chains in the given competition.
    Returns the list of IDs of the updated chains."""
    # TODO: Atomic.
    chains_was_verified = list(Chain.objects.filter(competition=competition) \
            .values_list('id', 'cache_is_verified'))
    ctasks = list(CompetitionTask.objects.filter(competition=competition) \
            .values_list('id', 'chain_id', 'cache_admin_solved_count'))

    not_verified = set()
    for ctask_id, chain_id, solved_count in ctasks:
        if chain_id is not None and \
                solved_count < competition.min_admin_solved_count:
            not_verified.add(chain_id)

    queries_args = []
    for chain_id, was_verified in chains_was_verified:
        verified = chain_id not in not_verified
        if was_verified != verified:
            queries_args.append((int(verified), chain_id))

    if queries_args:
        cursor = connection.cursor()
        cursor.executemany(
                "UPDATE `competition_chain` SET `cache_is_verified`=%s "
                "WHERE `id`=%s;", queries_args)
        transaction.commit_unless_managed()

    return [x[1] for x in queries_args]  # Extract IDs.


def update_chain_cache_is_verified(competition, chain):
    """Update cache_is_verified for the given chain."""
    verified = not CompetitionTask.objects \
            .filter(chain=chain,
                    cache_admin_solved_count__lt=
                        competition.min_admin_solved_count) \
            .exists()
    if chain.cache_is_verified != verified:
        chain.cache_is_verified = verified
        Chain.objects.filter(id=chain.id).update(cache_is_verified=verified)


def refresh_ctask_cache_admin_solved_count(competition):
    """Refresh cache_admin_solved_count for all ctasks in the given competition.
    Returns the list of IDs of the updated ctasks.
    DOES NOT update chain.cache_is_verified!"""
    # TODO: Atomic.
    ctasks_old_count = list(CompetitionTask.objects \
            .filter(competition=competition) \
            .values_list('id', 'cache_admin_solved_count'))

    # Not sure why we need `id` here, but for some reason it doesn't return all
    # the rows otherwise. (ivica)
    verified_ctask_ids = set(Submission.objects \
            .filter(team__competition_id=competition.id,
                    team__team_type=Team.TYPE_ADMIN_PRIVATE,
                    cache_is_correct=True) \
            .exclude(team__author=F('ctask__task__author')) \
            .values_list('id', 'ctask_id'))

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
                "UPDATE `competition_competitiontask` SET "
                "`cache_admin_solved_count`=%s WHERE `id`=%s;", queries_args)
        transaction.commit_unless_managed()

    return [x[1] for x in queries_args]  # Extract IDs.


def update_ctask_cache_admin_solved_count(competition, ctask, chain):
    """Update cache_admin_solved_count for the given ctask.
    Also takes care of chain.cache_is_verified."""
    solved_count = Submission.objects \
            .filter(ctask_id=ctask.id,
                    team__competition_id=competition.id,
                    team__team_type=Team.TYPE_ADMIN_PRIVATE,
                    cache_is_correct=True) \
            .exclude(team__author=F('ctask__task__author')) \
            .count()
    min_solved_count = competition.min_admin_solved_count

    before = ctask.cache_admin_solved_count >= min_solved_count
    ctask.cache_admin_solved_count = solved_count
    ctask.save()
    after = ctask.cache_admin_solved_count >= min_solved_count

    if before != after and chain is not None:
        update_chain_cache_is_verified(competition, chain)
