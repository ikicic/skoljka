from django.contrib.contenttypes.models import ContentType

from permissions.constants import VIEW
from permissions.utils import get_objects_with_permissions
from solution.models import Solution
from solution.templatetags.solution_tags import cache_solution_info
from task.models import Task

from activity.constants import *
from activity.models import Action

from django.db import connection

def get_recent_activities(user, max_count, exclude_user=None, target=None,
        action_object=None):
    """
        Returns recent activities visible to the given user.
        Selects also actors and actor profiles.

        Specifically, for SOLUTION_SUBMIT checks if the user can view the
        solution, and saves as ._hide_solution_link.
    """
    # Currently, to show recent N activities, we load 2 * N and then manually
    # iterate and remove those that are not visible to the current user. So,
    # the number of shown activities might not be constant. Also, the good
    # thing about this implementation is that we can preload all necessary data
    # about these activities.

    # TODO: refactor activities. for what do we need the cache, as we are
    # anyway loading half of the data again? also, cache must be updated
    # together with the data...

    activity = Action.objects
    if exclude_user and exclude_user.is_authenticated():
        activity = activity.exclude(actor=exclude_user)
    if target:
        activity = activity.filter(target=target)
    if action_object:
        activity = activity.filter(action_object=action_object)

    activity = activity.select_related('actor', 'actor__profile',
        'target_content_type').order_by('-id')[:int(max_count * 2)]
    activity = list(activity)
    activity_by_id = {x.id: x for x in activity}

    task_content_type_id = ContentType.objects.get_for_model(Task).id

    # Check permissions
    to_check = []           # list of (content_type_id, object_id, action_id)
    solutions_to_check = [] # list of (solution_id, atsk_id, action_id)
    kill = set()            # set of action_id to remove
    for x in activity:
        ttype = (x.type, x.subtype)

        # Hide 'marked as official' messages.
        # TODO: create a general way to hide solutions.
        if ttype == SOLUTION_AS_OFFICIAL:
            kill.add(x.id)
            continue

        if ttype in [TASK_ADD, FILE_ADD, LECTURE_ADD, SOLUTION_SUBMIT,
                SOLUTION_AS_SOLVED, SOLUTION_TODO, SOLUTION_AS_OFFICIAL]:
            # check task permissions...
            to_check.append((x.target_content_type_id, x.target_id, x.id))
            if ttype == SOLUTION_SUBMIT:
                # for ._hide_solution_link (kind of hack)
                solutions_to_check.append((x.action_object_id, x.target_id, x.id))
        elif ttype in [GROUP_ADD, GROUP_LEAVE]:
            # check group
            to_check.append((x.target_content_type_id, x.target_id, x.id))
        elif ttype in [POST_SEND, SOLUTION_RATE]:
            # SOLUTION_RATE behaves as POST_SEND for Solution comments...
            # TODO: this is stupid, separate POST_SEND into two different
            # constants?
            if x.target_content_type_id == task_content_type_id:
                to_check.append((x.target_content_type_id, x.target_id, x.id))
            else: # Solution
                try:
                    dummy, dummy, task_id, dummy, dummy = x.target_cache.split(POST_SEND_CACHE_SEPARATOR)
                    task_id = int(task_id)
                    to_check.append((task_content_type_id, task_id, x.id))
                    solutions_to_check.append((x.target_id, task_id, x.id))
                except ValueError:
                    kill.add(x.id)

    # Get content_type_id and object_id pairs
    pairs = [(a, b) for a, b, c in to_check]

    # Get objects
    visible_objects = get_objects_with_permissions(pairs, user, VIEW)

    # Mark invisible actions
    for content_type_id, object_id, action_id in to_check:
        if (content_type_id, object_id) not in visible_objects:
            kill.add(action_id)

    # Now, check solution accessibility...
    # Also, remove anything related to the official solutions.
    solutions_to_check_strict = []
    solution_ids = [id for id, task_id, action_id in solutions_to_check]
    solutions = dict(Solution.objects \
                             .filter(id__in=solution_ids) \
                             .values_list('id', 'is_official'))
    for solution_id, task_id, action_id in solutions_to_check:
        is_official = solutions.get(solution_id)
        # Remove if not found or official (first case should never happen).
        if is_official is None or is_official is True:
            kill.add(action_id)
            continue

        task = visible_objects.get((task_content_type_id, task_id))
        if not task:
            # kill.add(action_id) # already added
            continue
        if task.solution_settings != Task.SOLUTIONS_VISIBLE:
            solutions_to_check_strict.append((solution_id, action_id))

    if solutions_to_check_strict:
        solution_ids = [id for id, action_id in solutions_to_check_strict]
        # Ah, just reload those tasks...
        # TODO: or is it safe to reuse old task instances?
        solutions = list(Solution.objects   \
            .filter(id__in=solution_ids).select_related('task'))

        # Yes, this is the easiest way to do this...
        cache_solution_info(user, solutions)
        solution_by_id = {x.id: x for x in solutions}
        for solution_id, action_id in solutions_to_check_strict:
            solution = solution_by_id[solution_id]
            # TODO: separate can_view and obfuscate into two different methods?
            # we don't need should_obfuscate here...
            can_view, obfuscate = solution.check_accessibility(user,
                solution._cache_my_solution)
            if can_view:
                continue
            action = activity_by_id[action_id]
            if (action.type, action.subtype) in (SOLUTION_SUBMIT, SOLUTION_RATE):
                # don't kill, just remove link
                action._hide_solution_link = True
            else:
                kill.add(action_id)

    # And, finally, remove hidden activities and limit the size of the output.
    activity = [x for x in activity if x.id not in kill]
    return activity[:max_count]
