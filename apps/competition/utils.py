from django.db import connection, transaction

from competition.models import Chain, Competition, CompetitionTask, \
        Submission, Team, TeamMember

from collections import defaultdict
from datetime import timedelta

import re

# TODO(ivica): Add commit argument to all update_* methods.
def update_ctask_task(task, competition, chain, position, commit=False):
    """Updates task.name and .source. Does not save!"""
    task.name = u"{} - {} #{}".format(competition.name, chain.name, position)
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


def ctask_comment_class(ctask, current_user):
    if is_ctask_comment_important(ctask.comment.text):
        if ctask.task.author_id == current_user.id:
            return 'ctask-comment-important ctask-my'
        return 'ctask-comment-important'
    return ""


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

def refresh_submissions_cache_is_correct(submissions, ctasks=None):
    if ctasks is None:
        ctask_ids = set(submission.ctask_id for submission in submissions)
        ctasks = CompetitionTask.objects.filter(id__in=ctask_ids) \
                .select_related('competition__evaluator_version')

    ctasks = list(ctasks)
    ctasks_dict = {ctask.id: ctask for ctask in ctasks}

    for submission in submissions:
        ctask = ctasks_dict[submission.ctask_id]
        evaluator = ctask.competition.evaluator_version
        old = submission.cache_is_correct
        new = evaluator.check_result(ctask.descriptor, submission.result)
        if old != new:
            submission.cache_is_correct = new
            submission.save()

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
    test_teams = Team.objects \
            .filter(competition_id=competition_id, is_test=True) \
            .values_list('id', flat=True)
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
        is_test = key[0] in test_teams

        if is_solved:
            _key = 'S' # solved
        elif submission_count >= max_submissions_dict[key[1]]:
            _key = 'F' # failed
        else:
            _key = 'T' # tried

        _key = str(int(is_test)) + _key + str(key[1])
        result[_key] += 1

    return result
