from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.html import mark_safe

from skoljka.permissions.signals import objectpermissions_changed
from skoljka.solution.models import Solution, SolutionDetailedStatus
from skoljka.task.models import Task
from skoljka.usergroup.models import UserGroup
from skoljka.userprofile.models import UserProfile
from skoljka.utils import ncache
from skoljka.utils.decorators import cache_function

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
    solutions = (
        Solution.objects.filter_visible_tasks_for_user(user)
        .filter(detailed_status=UNRATED)
        .exclude(author_id=user.id)
        .select_related('task')
    )

    # Solution is interesting iff task is interesting. So, we are checking
    # tasks, not solutions. A task is interesting if the user wants to see the
    # solution, depending on the user preference and whether they themselves
    # solved the task.
    tasks = {}
    for x in solutions:
        if x.task_id not in tasks:
            tasks[x.task_id] = x.task

    # List of task ids.
    task_solutions_to_check = []  # solutions to check for CORRECT or AS_SOLVED
    interesting_tasks = set()

    for id, task in tasks.iteritems():
        if profile.check_solution_obfuscation_preference(task.difficulty_rating_avg):
            # User wouldn't like to see the solutions of the problem they
            # haven't solved. Hence, check if they solved it.
            task_solutions_to_check.append(id)
        else:
            interesting_tasks.add(id)

    if task_solutions_to_check:
        tasks_solved_by_user = Solution.objects.filter(
            author_id=user.id,
            task_id__in=task_solutions_to_check,
            detailed_status__in=[CORRECT, AS_SOLVED],
        ).values_list('task_id', flat=True)

        interesting_tasks.update(tasks_solved_by_user)

    # Finally, filter solutions with interesting tasks.
    return [x for x in solutions if x.task_id in interesting_tasks]


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
            new_count = (
                sum(x.date_created >= _time for x in unrated) if _time else len(unrated)
            )
            old_count = len(unrated) - new_count

            old = (
                '<span class="nav-sol-old-cnt">({}{})</span>'.format(
                    '+' if new_count else '', old_count
                )
                if old_count
                else ''
            )

            new = (
                '<span class="nav-sol-new-cnt">({})</span>'.format(new_count)
                if new_count
                else ''
            )

            html = '{} {}'.format(new, old)
            output['unrated_solutions_new'] = new_count
            output['unrated_solutions_html'] = mark_safe(html)

    return output


######################
# Cache invalidation.
######################

# TODO: some detailed_status changes will call this method twice (because
# some statistics in UserProfile are also being updated)
@receiver(objectpermissions_changed, sender=Task)  # permissions
@receiver(post_save, sender=Task)  # hidden
@receiver(post_save, sender=UserGroup)  # group m2m change
@receiver(post_save, sender=UserProfile)  # options
@receiver(post_delete, sender=Solution)  # some weird cases
@receiver(post_save, sender=Solution)  # obvious, detailed_status
def _invalidate_evaluator_namespace(sender, **kwargs):
    if not hasattr(kwargs['instance'], '_dummy_update'):
        ncache.invalidate_namespace(EVALUATOR_NAMESPACE)
