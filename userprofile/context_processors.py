from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.html import mark_safe

from permissions.constants import VIEW
from permissions.signals import objectpermissions_changed
from permissions.utils import get_object_ids_with_exclusive_permission
from solution.models import Solution, DETAILED_STATUS
from task.models import Task
from usergroup.models import UserGroup
from skoljka.utils import ncache
from skoljka.utils.decorators import cache_function

from userprofile.models import UserProfile

from collections import defaultdict

EVALUATOR_NAMESPACE = 'UsrPrEval'
UNRATED_SOL_CNT_KEY_FORMAT = 'UnratedSolutions{0.pk}'

NOT_RATED_STATUS = DETAILED_STATUS['submitted_not_rated']

@cache_function(namespace=EVALUATOR_NAMESPACE, key=UNRATED_SOL_CNT_KEY_FORMAT)
def find_unrated_solutions(user):
    """
        Returns the list of all unrated solutions visible and important
        (not obfuscated) to the given user.
    """
    # TODO: check task.solution_settings!!

    profile = user.get_profile()

    # For some reason had to put detailed_status here...
    solutions = Solution.objects  \
        .filter(detailed_status=NOT_RATED_STATUS) \
        .exclude(author_id=user.id) \
        .select_related('task', 'author')

    # Maybe == before checked whether user solved this problem.
    did_solve_task = set()  # check whether user solved the task
    maybe_check = set()     # check both permissions and user's solution
    to_check = set()        # check only permissions
    result = []             # instances of important unrated solutions
    unrated_solution_count = 0

    id_to_solution = {x.id: x for x in solutions}
    task_id_to_solutions = defaultdict(list)

    for x in solutions:
        task_id_to_solutions[x.task_id].append(x)

        maybe_obfuscated = not profile.show_unsolved_task_solutions      \
            and x.task.difficulty_rating_avg >= profile.hide_solution_min_diff

        # Yeah, a lot of cases...
        if maybe_obfuscated:
            did_solve_task.add(x.task_id)
            if x.task.hidden and x.task.author_id != user.id:
                maybe_check.add(x.task_id)
        else:
            if x.task.hidden and x.task.author_id != user.id:
                to_check.add(x.task_id)
            else:
                # definitely visible
                result.append(x)

    if did_solve_task:
        my_solved_tasks = set(Solution.objects.filter(author_id=user.id,
            task_id__in=did_solve_task).values_list('task_id', flat=True))

        # Hidden (and not user's task):
        # Even if user solved the problem, he/she might not have the permission
        # to view other solutions. Weird case, handle as you wish.
        to_check |= maybe_check & my_solved_tasks
        # Non hidden:
        diff = my_solved_tasks - maybe_check
        result.extend([id_to_solution[id] for id in diff])

    if to_check:
        # WARNING: checking permissions manually!
        task_ids = get_object_ids_with_exclusive_permission(user, VIEW,
            model=Task, filter_ids=to_check)
        result.extend(sum([task_id_to_solutions[id] for id in task_ids], []))

    return result

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
