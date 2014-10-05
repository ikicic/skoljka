from competition.models import Chain, CompetitionTask, Submission, Team, \
        TeamMember

from collections import defaultdict

def refresh_teams_cache_score(teams):
    teams = list(teams)
    if not teams:
        return

    team_ids = [team.id for team in teams]
    competition_ids = [team.competition_id for team in teams]
    competition_ids = list(set(competition_ids))

    all_ctasks = list(CompetitionTask.objects.filter(
            competition_id__in=competition_ids))
    all_chains = list(Chain.objects.filter(competition_id__in=competition_ids))
    all_submissions = Submission.objects.filter(team_id__in=team_ids) \
            .values_list('team_id', 'ctask_id', 'cache_is_correct')

    ctasks_dict = {ctask.id: ctask for ctask in all_ctasks}
    chains_dict = {chain.id: chain for chain in all_chains}

    is_solved = defaultdict(bool)
    for team_id, ctask_id, cache_is_correct in all_submissions:
        is_solved[(team_id, ctask_id)] |= cache_is_correct

    for chain in all_chains:
        chain.ctasks = []
    for ctask in all_ctasks:
        chains_dict[ctask.chain_id].ctasks.append(ctask)

    for team in teams:
        # OPTIMIZE: split by competitions
        score = 0
        for chain in all_chains:
            if chain.competition_id != team.competition_id:
                continue
            score += sum(ctask.score for ctask in chain.ctasks \
                    if is_solved.get((team.id, ctask.id)))
            if all(is_solved.get((team.id, ctask.id)) \
                    for ctask in chain.ctasks):
                score += chain.bonus_score
        team.cache_score = score
        team.save()

def lock_ctasks_in_chain(ctasks):
    locked = False
    for ctask in ctasks:
        ctask.t_is_locked = locked and not ctask.t_is_solved
        if not ctask.t_is_solved \
                and ctask.t_submission_count < ctask.max_submissions:
            locked = True

def check_single_chain(chain, team, preloaded_ctask=None, competition=None):
    ctasks = list(CompetitionTask.objects.filter(chain=chain) \
            .order_by('chain_position', 'id') \
            .only('id', 'max_submissions'))
    if preloaded_ctask:
        ctasks = [preloaded_ctask if ctask.id == preloaded_ctask.id else ctask \
                for ctask in ctasks]

    ctasks_dict = {ctask.id: ctask for ctask in ctasks}
    submissions = Submission.objects \
            .filter(ctask_id__in=ctasks_dict.keys(), team=team) \
            .values_list('ctask_id', 'cache_is_correct')

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

    for ctask_id, cache_is_correct in submissions:
        ctask = ctasks_dict[ctask_id]
        ctask.t_submission_count += 1
        ctask.t_is_solved |= cache_is_correct

    lock_ctasks_in_chain(ctasks)

    return ctasks

def refresh_submissions_cache_is_correct(submissions, ctasks=None):
    if ctasks is None:
        ctask_ids = set(submission.ctask_id for submission in submissions)
        ctasks = CompetitionTask.objects.filter(id__in=ctask_ids)

    ctasks = list(ctasks)
    ctasks_dict = {ctask.id: ctask for ctask in ctasks}

    for submission in submissions:
        ctask = ctasks_dict[submission.ctask_id]
        old = submission.cache_is_correct
        new = ctask.check_result(submission.result)
        if old != new:
            submission.cache_is_correct = new
            submission.save()

def get_teams_for_user_ids(user_ids):
    team_members = list(TeamMember.objects.filter(member_id__in=set(user_ids)) \
            .select_related('team') \
            .only('member', 'team'))

    return {x.member_id: x.team for x in team_members}

def get_ctask_statistics(competition):
    """
    # TODO: documentation
    """
    max_submissions_dict = dict(CompetitionTask.objects \
            .filter(competition=competition) \
            .values_list('id', 'max_submissions'))
    test_teams = Team.objects.filter(competition=competition, is_test=True) \
            .values_list('id', flat=True)
    correct_submissions = Submission.objects.filter(
            ctask__competition_id=competition.id) \
                    .values_list('team_id', 'ctask_id', 'cache_is_correct')

    submission_count_dict = defaultdict(int)
    is_solved_dict = defaultdict(bool)
    for team_id, ctask_id, cache_is_correct in correct_submissions:
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
