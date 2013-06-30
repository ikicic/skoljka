from permissions.constants import VIEW_SOLUTIONS
from permissions.utils import get_object_ids_with_exclusive_permission
from solution.models import DETAILED_STATUS, Solution

from task.models import Task

CORRECT = DETAILED_STATUS['correct']

def check_prerequisites_for_tasks(tasks, user):
    """
        Checks if all of the prerequisite tasks have been solved for each of
        the given task.
        Prerequisites are met if:
            a) there are no prerequisites at all
            b) the user is the author of the task
            c) user solved all of the necessary tasks
            d) user has VIEW_SOLUTIONS permission.
    """
    to_check = [] # for solutions or VIEW_SOLUTIONS
    for x in tasks:
        x._cache_prerequisites = x._get_prerequisites()
        if not x._cache_prerequisites or x.author_id == user.id:
            x.cache_prerequisites_met = True
        else:
            to_check.append(x)

    if not user.is_authenticated():
        for x in to_check:
            x.cache_prerequisites_met = False
        return

    if to_check:
        # All tasks for which solutions we are interested in.
        all_tasks = sum([x._cache_prerequisites for x in tasks], [])

        solutions = set(Solution.objects.filter(author_id=user.id,
                task_id__in=all_tasks, detailed_status=CORRECT) \
            .values_list('task_id', flat=True))

        another_check = [] # VIEW_SOLUTIONS check
        for x in to_check:
            if set(x._cache_prerequisites).issubset(solutions):
                x.cache_prerequisites_met = True
            else:
                another_check.append(x)

        if another_check:
            # Tasks with VIEW_SOLUTIONS permission
            ids = [x.id for x in another_check]
            # Author already checked.
            accepted = set(get_object_ids_with_exclusive_permission(user,
                VIEW_SOLUTIONS, model=Task, filter_ids=ids))
            for x in another_check:
                x.cache_prerequisites_met = x.id in accepted


def task_similarity(first, second):
    a = set(first.tags.values_list('id', 'weight'))
    b = set(second.tags.values_list('id', 'weight'))
    tag_sim = 0
    for id, weight in (a & b):
        tag_sim += weight

    # difficulty similarity
    if first.difficulty_rating_avg == 0.0 or second.difficulty_rating_avg == 0.0:
        diff_sim = 0.1
    else:
        diff_sim = 1. / (1 + (first.difficulty_rating_avg - second.difficulty_rating_avg) ** 2)

    # total similarity
    return tag_sim * diff_sim
