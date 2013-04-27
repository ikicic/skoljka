from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from permissions.constants import VIEW
from permissions.signals import objectpermissions_changed
from permissions.utils import get_object_ids_with_exclusive_permission
from solution.models import Solution, DETAILED_STATUS
from task.models import Task
from usergroup.models import UserGroup
from skoljka.utils import ncache
from skoljka.utils.decorators import cache_function

from userprofile.models import UserProfile

EVALUATOR_NAMESPACE = 'UsrPrEval'
UNRATED_SOL_CNT_KEY_FORMAT = 'unratedSolCnt{0.pk}'

NOT_RATED_STATUS = DETAILED_STATUS['submitted_not_rated']

@cache_function(namespace=EVALUATOR_NAMESPACE, key=UNRATED_SOL_CNT_KEY_FORMAT)
def calc_unrated_solution_count(user):
    profile = user.get_profile()

    # For some reason had to put detailed_status here...
    solutions = Solution.objects  \
        .filter(detailed_status=NOT_RATED_STATUS) \
        .exclude(author_id=user.id) \
        .select_related('task')     \
        .only('id', 'detailed_status', 'task__author',
            'task__difficulty_rating_avg', 'task__hidden')

    # Maybe == before checked whether user solved this problem.
    did_solve_task = set()  # check whether user solved the task
    maybe_check = set()     # check both permissions and user's solution
    to_check = set()        # check only permissions
    unrated_solution_count = 0
    for x in solutions:
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
                unrated_solution_count += 1

    if did_solve_task:
        my_solved_tasks = set(Solution.objects.filter(author_id=user.id,
            task_id__in=did_solve_task).values_list('task_id', flat=True))

        # Hidden (and not user's task):
        # Even if user solved the problem, he/she might not have the permission
        # to view other solutions. Weird case, handle as you wish.
        to_check |= maybe_check & my_solved_tasks
        # Non hidden:
        unrated_solution_count += len(my_solved_tasks - maybe_check)

    if to_check:
        # WARNING: checking permissions manually!
        unrated_solution_count += get_object_ids_with_exclusive_permission(
            user, VIEW, model=Task, filter_ids=to_check).count()

    return unrated_solution_count

def userprofile(request):
    user = request.user
    if not user.is_authenticated():
        return {}

    profile = user.get_profile()

    result = {}
    if profile.evaluator:
        result['t_unrated_solution_count'] = calc_unrated_solution_count(user)

    return result

######################
# Cache invalidation.
######################

@receiver(objectpermissions_changed, sender=Task)   # permissions
@receiver(post_save, sender=Task)           # task hidden/not hidden
@receiver(post_save, sender=UserGroup)      # group m2m change
@receiver(post_save, sender=UserProfile)    # detailed_status changes also!
@receiver(post_delete, Solution)            # some weird case
def _invalidate_evaluator_namespace(sender, **kwargs):
    ncache.invalidate_namespace(EVALUATOR_NAMESPACE)
