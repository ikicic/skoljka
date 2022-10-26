from collections import defaultdict

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.html import mark_safe

from skoljka.permissions.constants import VIEW_SOLUTIONS
from skoljka.permissions.signals import objectpermissions_changed
from skoljka.permissions.utils import get_object_ids_with_exclusive_permission
from skoljka.solution.models import Solution, SolutionDetailedStatus
from skoljka.task.models import Task
from skoljka.usergroup.models import UserGroup
from skoljka.utils import ncache
from skoljka.utils.decorators import cache_function

from skoljka.userprofile.models import UserProfile

EVALUATOR_NAMESPACE = 'UsrPrEval'
UNRATED_SOL_CNT_KEY_FORMAT = 'UnratedSolutions{0.pk}'

UNRATED = SolutionDetailedStatus.SUBMITTED_NOT_RATED
CORRECT = SolutionDetailedStatus.SUBMITTED_CORRECT
AS_SOLVED = SolutionDetailedStatus.AS_SOLVED

@cache_function(namespace=EVALUATOR_NAMESPACE, key=UNRATED_SOL_CNT_KEY_FORMAT)
def find_unrated_solutions(user):
    """
    Returns the list of all unrated solutions visible and important (not
    obfuscated) to the given user.
    """
    profile = user.get_profile()

    # Get all unrated solutions. Remove nonvisible, remove my own solutions.
    solutions = Solution.objects  \
        .filter_visible_tasks_for_user(user)    \
        .filter(detailed_status=UNRATED) \
        .exclude(author_id=user.id) \
        .select_related('task')

    # Solution is interesting iff task is interesting. So, we are checking
    # tasks, not solutions.
    tasks = {}
    for x in solutions:
        if x.task_id not in tasks:
            tasks[x.task_id] = x.task

    # Task is accepted if
    #   a) we have permission to view other solutions (check task & my solution)
    #   b) we want to view solutions (check profile & my solution)

    # List of task ids
    get_solution_correct = [] # solutions to check for CORRECT
    get_solution_solved = []  # solutions to check for CORRECT or AS_SOLVED
    get_view_solutions = []   # VIEW_SOLUTIONS permissions to check

    with_permission = []      # tasks with permission to view solutions

    for id, x in tasks.iteritems():
        if x.author_id != user.id:
            if x.solution_settings == Task.SOLUTIONS_NOT_VISIBLE:
                # Visible only with the VIEW_SOLUTIONS permission
                get_view_solutions.append(id)
            elif x.solution_settings == Task.SOLUTIONS_VISIBLE_IF_ACCEPTED:
                # Visible with VIEW_SOLUTIONS, or with a correct solution
                get_solution_correct.append(id)
            else:
                with_permission.append(id)
        else:
            with_permission.append(id)

        if profile.check_solution_obfuscation_preference(
                x.difficulty_rating_avg):
            # User wouldn't like to see the solutions of the problem he/she
            # didn't solve. Check for the solution then.
            get_solution_solved.append(id)

    get_any_solution = get_solution_correct + get_solution_solved
    if get_any_solution:
        # dict {task_id: detailed_status}
        my_solutions = dict(Solution.objects
            .filter(author_id=user.id, task_id__in=get_any_solution,
                detailed_status__in=[CORRECT, AS_SOLVED])
            .values_list('task_id', 'detailed_status'))

        # Accept SOLUTIONS_VISIBLE_IF_ACCEPTED tasks if the solution is correct
        for id in get_solution_correct:
            if my_solutions.get(id) == CORRECT:
                with_permission.append(id)
            else:
                # no solution --> check for permissions
                get_view_solutions.append(id)
    else:
        my_solutions = {}

    if get_view_solutions:
        # WARNING: checking permissions manually!
        with_permission.extend(get_object_ids_with_exclusive_permission(user,
            VIEW_SOLUTIONS, model=Task, filter_ids=get_view_solutions))

    # Now when I know which tasks I'm able to see, filter those I want to see.
    # Remember, I want to see if 1) I solved the problem OR 2) I'm fine with
    # seeing the solution anyway (depending on the difficulty rating).
    accepted_tasks = set(id for id in with_permission   \
            if id in my_solutions
                or not profile.check_solution_obfuscation_preference(
                    tasks[id].difficulty_rating_avg))

    # Finally, filter solutions with accepted tasks
    return [x for x in solutions if x.task_id in accepted_tasks]

def userprofile(request):
    user = request.user
    if not user.is_authenticated():
        return {}

    profile = user.get_profile()

    output = {}
    if profile.evaluator:
        output['unrated_solutions'] = unrated = find_unrated_solutions(user)

        if unrated:
            _time = profile.eval_sol_last_view
            new_count = sum(x.date_created >= _time for x in unrated) \
                if _time else len(unrated)
            old_count = len(unrated) - new_count

            old = '<span class="nav-sol-old-cnt">({}{})</span>'.format(
                    '+' if new_count else '', old_count) \
                if old_count else ''

            new = '<span class="nav-sol-new-cnt">({})</span>'.format(new_count) \
                if new_count else ''

            html = '{} {}'.format(new, old)
            output['unrated_solutions_new'] = new_count
            output['unrated_solutions_html'] = mark_safe(html)

    return output

######################
# Cache invalidation.
######################

# TODO: some detailed_status changes will call this method twice (because
# some statistics in UserProfile are also being updated)
@receiver(objectpermissions_changed, sender=Task)   # permissions
@receiver(post_save, sender=Task)           # hidden, solution settings
@receiver(post_save, sender=UserGroup)      # group m2m change
@receiver(post_save, sender=UserProfile)    # options
@receiver(post_delete, sender=Solution)     # some weird cases
@receiver(post_save, sender=Solution)       # obvious, detailed_status
def _invalidate_evaluator_namespace(sender, **kwargs):
    if not hasattr(kwargs['instance'], '_dummy_update'):
        ncache.invalidate_namespace(EVALUATOR_NAMESPACE)
