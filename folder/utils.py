from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import pre_save, post_save, pre_delete,   \
    m2m_changed
from django.dispatch import receiver

from permissions.constants import VIEW
from permissions.signals import objectpermissions_changed
from search.models import SearchCacheElement
from search.utils import reverse_search
from solution.models import Solution
from tags.utils import get_object_tagged_items
from task.models import Task
from usergroup.models import UserGroup
from skoljka.utils import ncache

from folder.models import Folder, FolderTask, FOLDER_NAMESPACE_FORMAT,  \
    FOLDER_NAMESPACE_FORMAT_ID

import re

def get_folder_template_data(path, user, flags):
    """
        Given URI path, finds related Folder and returns all necessary
        template data, such as folder menu.
        Used for parsing HTTP_REFERER.
    """

    if not re.match('^/folder/\d+/[-a-zA-Z0-9]*$', path):
        return None

    id = int(path[8:path.find('/', 8)])

    try:
        folder = Folder.objects.get(id=id)
    except Folder.DoesNotExist:
        return None

    # Retrieve all necessary information
    return folder.get_template_data(user, flags)

def get_task_folder_ids(task):
    """
        Returns the list of IDs of all folders containing given task.
        Combines result of many-to-many relation and folder-filters.
    """
    tags = [x.tag for x in get_object_tagged_items(task)]

    # One possible solution is:
    #   Folder.objects.for_user(user, permission)  \
    #       .filter(tasks=task, search_cache_elements__cache=search_cache) \
    #       .distinct()
    # but the complexity of this query is O(count(Folder)).
    # That's why we separately take IDs from FolderTask and IDs from
    # reverse_cache and then select them through their IDs.

    # Folders with many-to-many relation
    m2m_ids = FolderTask.objects.filter(task=task).values_list('folder_id', flat=True)

    # Folders with tag filter
    search_cache = reverse_search([x.name for x in tags])
    if search_cache:
        content_type = ContentType.objects.get_for_model(Folder)
        search_ids = SearchCacheElement.objects.filter(cache=search_cache,
            content_type=content_type).values_list('object_id', flat=True)
    else:
        search_ids = []

    ids = list(m2m_ids) + list(search_ids)

    # Remove duplicates (does not preserve order)
    return list(set(ids))

def get_task_folders(task, user=None, check_permissions=True, permission=VIEW):
    """
        Extension to get_task_folder_ids. Returns folder instances instead
        of IDs. Also, checks user permissions if required.
    """
    ids = get_task_folder_ids(task)

    if check_permissions:
        return Folder.objects.for_user(user, permission)    \
            .filter(id__in=ids).distinct()
    else:
        return Folder.objects.filter(id__in=ids)


class FolderInfo:
    """
        Helper struct used in refresh_path_cache.
    """
    def __init__(self, id):
        self.id = id
        self.parent = None

        self.ancestors = None

    def __repr__(self):
        return '#{} {}'.format(self.id, getattr(self.parent, 'id', None))

    def recursion(self, folders):
        if self.ancestors is not None:
            return # already done

        if self.parent is None: # if root
            self.ancestors = ''
        else:
            if self.parent.ancestors is None:
                self.parent.recursion(folders)

            self.ancestors = self.parent.ancestors + str(self.parent.id) + ','

def refresh_cache_fields(queryset):
    """
        Refresh folder cache information as
            cache_ancestor_ids.

        Although it is possible to select only a subset of folders,
        please select all folders when using this action.
    """
    # This code is a modification of the earlier one, where more info was
    # saved (cache_path).
    folder_list = queryset.values_list('id', 'parent_id')

    # TODO: refresh .cache_tags!

    folders = {id: FolderInfo(id)
        for (id, parent_id) in folder_list}

    for id, parent_id in folder_list:
        folders[id].parent = parent_id and folders[parent_id]

    for f in folders.itervalues():
        f.recursion(folders)

    for id, f in folders.iteritems():
        Folder.objects.filter(id=id).update(cache_ancestor_ids=f.ancestors[:-1])


######################
# Cache invalidation.
######################

# Here, and not in models.py, to avoid import cycles.

def invalidate_cache_for_folder_ids(folder_ids):
    """
        Something to avoid, or be extremely careful with.
    """
    namespaces = [FOLDER_NAMESPACE_FORMAT_ID.format(x) for x in folder_ids]
    ncache.invalidate_namespaces(namespaces)

def invalidate_cache_for_folders(folders):
    """
        Something to avoid, or be extremely careful with.
    """
    namespaces = [FOLDER_NAMESPACE_FORMAT.format(x) for x in folders]
    ncache.invalidate_namespaces(namespaces)

def invalidate_folder_cache_for_task(task):
    print 'invalidating for: ', task
    # One could replace .task with .task_id, but the problem is with the
    # methods get_task_folder_ids is using.
    invalidate_cache_for_folder_ids(get_task_folder_ids(task))

@receiver(objectpermissions_changed, sender=Folder)
def _invalidate_on_folder_permissions_update(sender, **kwargs):
    # Invalidate itself.
    namespace = FOLDER_NAMESPACE_FORMAT.format(kwargs['instance'])
    ncache.invalidate_namespace(namespace)

@receiver(pre_save, sender=Solution)
def _invalidate_on_solution_update(sender, **kwargs):
    instance = kwargs['instance']
    if instance._original_detailed_status != instance.get_detailed_status():
        invalidate_folder_cache_for_task(instance.task)

@receiver(pre_delete, sender=Solution)
def _invalidate_on_solution_delete(sender, **kwargs):
    invalidate_folder_cache_for_task(kwargs['instance'].task)

@receiver(objectpermissions_changed, sender=Task)
def _invalidate_on_task_permissions_update(sender, **kwargs):
    invalidate_folder_cache_for_task(kwargs['instance'])

# For some reason User.groups.through.objects.get_or_create does not send
# any signals. (?) Then have to catch the change via UserGroup model, which
# updates member count and similar info.
# This actually handles both add / remove with only one signal, independent of
# number of users added / removed to the Group.
@receiver(post_save, sender=UserGroup)
def _invalidate_on_usergroup_update(sender, **kwargs):
    folder_ids = Folder.objects    \
        .filter(hidden=True, permissions__group_id=kwargs['instance'].group_id) \
        .values_list('id', flat=True).distinct()
    invalidate_cache_for_folder_ids(folder_ids)
