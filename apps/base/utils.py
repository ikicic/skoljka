from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from folder.models import FOLDER_NAMESPACE_FORMAT_ID, Folder, FolderTask
from task.models import Task
from skoljka.libs.decorators import cache_function, \
        get_cache_function_full_key
from skoljka.libs import ncache

FEATURED_FOLDER_ID = getattr(settings, 'FEATURED_LECTURES_FOLDER_ID', None)
FEATURED_LECTURES_FOLDER_NAMESPACE = \
        FOLDER_NAMESPACE_FORMAT_ID.format(FEATURED_FOLDER_ID)

def can_edit_featured_lectures(user):
    """Check if the given user can edit featured lectures."""
    return user.is_staff


@cache_function(namespace=FEATURED_LECTURES_FOLDER_NAMESPACE)
def _get_featured_lectures_cached():
    try:
        folder = Folder.objects.get(id=FEATURED_FOLDER_ID)
    except Folder.DoesNotExist:
        return None  # This is the homepage, don't just throw exceptions.

    # Remove all hidden task. Featured lectured should work as fast as
    # possible, and we don't want to cache this for each user separately.
    tasks = list(folder.get_queryset(None, no_perm_check=True))
    if any(task.hidden for task in tasks):
        # TODO: log
        print "WARNING! Some featured lectures are hidden! Ignoring them."
        tasks = [task for task in tasks if not task.hidden]

    return tasks


def get_featured_lectures():
    """Return the list of all featured lectures (Task objects).

    Lecture is featured if it is contained in the folder with ID equal to
    settings.FEATURED_LECTURES_FOLDER_ID. All hidden tasks are automatically
    ignored.

    The result is cached in the folder's cache namespace.
    """
    if not FEATURED_FOLDER_ID:
        return None  # No cache queries if featured lectures not used at all.
    return _get_featured_lectures_cached()


@receiver(post_save, sender=Task)
def _invalidate_on_task_update(sender, **kwargs):
    instance = kwargs['instance']
    if instance.is_lecture and FolderTask.objects.filter(
            folder_id=FEATURED_FOLDER_ID, task_id=instance.id).exists():
        # It is fine to make an additional database query to check if
        # invalidation is necessary. (one query vs a lot of queries)
        full_key = get_cache_function_full_key(_get_featured_lectures_cached,
                namespace=FEATURED_LECTURES_FOLDER_NAMESPACE)
        ncache.invalidate_full_key(full_key)
