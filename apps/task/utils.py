from __future__ import print_function

from folder.models import Folder, FolderTask
from folder.utils import get_task_folder_ids, invalidate_cache_for_folders, \
        prepare_folder_menu
from mathcontent.models import MathContent
from permissions.constants import VIEW_SOLUTIONS
from permissions.models import ObjectPermission
from permissions.utils import get_object_ids_with_exclusive_permission
from solution.models import Solution, SolutionDetailedStatus
from tags.models import Tag, TaggedItem
from tags.utils import set_tags

from task.models import Task

import time

CORRECT = SolutionDetailedStatus.SUBMITTED_CORRECT

# TODO: does EDIT imply VIEW_SOLUTIONS?

def check_prerequisites_for_task(task, user, perm=None):
    """
    Slighty optimized version of check_prerequisites_for_tasks for a single
    task. Uses already loaded list of permissions `perm`, if given.

    Saves the result in:
        task.cache_prerequisites_met (Boolean)

    Return value:
        task.cache_prerequisites_met (Boolean)

    Does not check visibility!
    """

    # Cheap tests first, expensive last.
    if task.author_id == user.id:
        task.cache_prerequisites_met = True
    else:
        prerequisites = task._get_prerequisites()
        if not prerequisites:
            task.cache_prerequisites_met = True
        elif user.is_anonymous():
            task.cache_prerequisites_met = False
        elif (perm is not None and VIEW_SOLUTIONS in perm) \
                or (perm is None and task.user_has_perm(user, VIEW_SOLUTIONS)):
            task.cache_prerequisites_met = True
        else:
            solved_tasks = Solution.objects.filter(author_id=user.id,
                    task_id__in=prerequisites, detailed_status=CORRECT) \
                .values_list('task_id', flat=True)

            task.cache_prerequisites_met = \
                    set(solved_tasks) == set(prerequisites)

    return task.cache_prerequisites_met


def check_prerequisites_for_tasks(tasks, user):
    """
    Checks if all of the prerequisite tasks have been solved for each of the
    given task.

    Saves the result in:
        task.cache_prerequisites_met

    Return value:
        None

    Does not check visibility!

    Prerequisites are met if:
        a) user is the author of the task
        b) there are no task prerequisites at all
        c) user solved all of the prerequisites
        d) user has the VIEW_SOLUTION permission
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

        solved_tasks = set(Solution.objects.filter(author_id=user.id,
                task_id__in=all_tasks, detailed_status=CORRECT) \
            .values_list('task_id', flat=True))

        another_check = [] # VIEW_SOLUTIONS check
        for x in to_check:
            if set(x._cache_prerequisites).issubset(solved_tasks):
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

def get_task_folder_data(task, user):
    folder_ids = get_task_folder_ids(task)  # unsafe, no permission check!
    folders = list(Folder.objects.filter(id__in=folder_ids))
    folder_data = prepare_folder_menu(folders, user) # safe

    # For now, folder is not considered to be the owner of the tasks, but only
    # a collection. Therefore, if the user has no access to any of the
    # task's folders, he/she might still have the access to the task itself.

    # True, automatically removing access to the task if the user has no
    # access to its containers is a really great feature. But, it is
    # too complicated - advanced permission check should be added to everything
    # related to the task (e.g. editing, solutions, permissions editing etc.)

    return folder_data



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


def create_tasks_from_json(description):
    """
    Given a list of Task description dictionaries, create Task instances,
    together with other related objects.

    Supported special data:
        _content (string) - the text of the task, MathContent text
        _folder_id (int) - ID of the folder where to add the task
        _folder_position (int) - position in that folder
        _tags (string) - a comma-separated list of tags
        _difficulty (int) - difficulty rating to be assigned by the author
        _permissions (dict {"permission type ID": [list of group IDs]})
                - group permission to automatically assign.
                - (ID is a string because in JSON keys must be strings)

    All other elements with an underscore are ignored.

    Params:
        description (list): list of dict object, describing the tasks

    Returns:
        A list of the new Task objects.

    If an exception is thrown in the middle of the process, the exception is
    caputed, the message changed, and raised again.
    """
    # Approx.
    task_fields = set(Task._meta.get_all_field_names())
    task_fields |= set(x + '_id' for x in task_fields)

    created_objects = []
    created_tasks = []
    message_list = []

    # List of objects to create
    folder_tasks = []
    object_permissions = []

    # Measure time.
    start_time = time.time()

    def elapsed_time():
        return "{:.6f}".format(time.time() - start_time)

    try:
        for k, desc in enumerate(description):
            message_list.append("Creating task #0.".format(k + 1))
            print(elapsed_time(), "Creating task #{}.".format(k + 1))

            # First, prepare data to be able to create Task.
            # --- math content ---
            math_content = MathContent()
            math_content.text = desc['_content']
            message_list.append(desc['_content'])
            math_content.save()
            created_objects.append(math_content)
            print(elapsed_time(), "    ", "Saved math content.")

            # Second, create Task.
            task = Task()
            task.content = math_content
            for key, value in desc.iteritems():
                if key[0] != '_' and key in task_fields:
                    setattr(task, key, value)
            task.save()
            created_objects.append(task)
            created_tasks.append(task)
            print(elapsed_time(), "    ", "Saved task.")

            # Third, save other data.

            # --- tags ---
            tags = desc.get('_tags', '')
            set_tags(task, tags)
            print(elapsed_time(), "    ", "Saved tags.")

            # --- difficulty ---
            difficulty = desc.get('_difficulty')
            if difficulty:
                task.difficulty_rating.update(task.author, int(difficulty))
            print(elapsed_time(), "    ", "Saved difficulty.")

            # --- folder ids ---
            folder_id = desc.get('_folder_id')
            if folder_id is not None:
                folder_tasks.append(FolderTask(
                        folder_id=folder_id, task=task,
                        position=desc.get('_folder_position', 0)))

            # --- group permissions ---
            for perm, group_ids in desc.get('_permissions', {}).iteritems():
                for group_id in group_ids:
                    object_permissions.append(ObjectPermission(
                            content_object=task, group_id=group_id,
                            permission_type=perm))

        print(elapsed_time(), "Done storing tasks.")

        FolderTask.objects.bulk_create(folder_tasks)
        print(elapsed_time(), "Done storing folder tasks.")
        ObjectPermission.objects.bulk_create(object_permissions)
        print(elapsed_time(), "Done storing object permissions.")
    except Exception as e:
        # This should remove all dependend objects.
        for obj in created_objects:
            obj.delete()

        print(elapsed_time(), "Exception:", e)
        message_list.append("Reverting changes...")
        message = "\n".join(message_list) + "\n\n" + traceback.format_exc()
        raise type(e)(message)
    finally:
        print(elapsed_time(), "Starting folder cache invalidation.")
        # SPEED: Don't invalidate everything.
        invalidate_cache_for_folders(Folder.objects.all())
        print(elapsed_time(), "Folders invalidated. Done.")
    return created_tasks
