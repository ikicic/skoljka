from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import pre_save, post_save, pre_delete,   \
    m2m_changed
from django.dispatch import receiver

from permissions.constants import VIEW
from permissions.utils import get_object_ids_with_exclusive_permission
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

from collections import Counter, defaultdict


def get_task_folder_ids(task):
    """
        Returns the list of IDs of all folders containing given task.
        Combines result of many-to-many relation and folder-filters.

        Does not check permissions, and not supposed to do any checks.
    """
    # Implementation of permission check is very complicated! Do not implement
    # it here. prepare_folder_menu can be used if needed. If you really need
    # permission check, without menu data, refactor / split prepare_folder_menu
    # into separated utility methods, but do not change this method!

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

def prepare_folder_menu(folders, user):
    """
        Given list of folders, prepare folder menu showing all those folders
        at once. Ignores from input all folder inaccessible for the given user.

        Returns dict with following keys:
            folder_children - dictionary {folder.id: list of children instances}
            folder_tree - HTML of folder tree
    """
    # Note: This method calls Folder.many_get_user_stats, which makes it
    # sometimes very slow. Actually, the method is relatively fast.
    # Still, more optimizations are welcome here, because this method is called
    # on almost every query...

    # Pick all ancestor ids
    ancestor_ids = sum([x.cache_ancestor_ids.split(',') for x in folders], [])
    ancestor_ids = [int(x) for x in ancestor_ids if x]

    # For permission check. Note that we put here only elements from
    # .cache_ancestor_ids!
    ancestor_counter = Counter(ancestor_ids)

    # Now add original folders and remove duplicates
    ancestor_ids.extend([x.id for x in folders])
    ancestor_ids = set(ancestor_ids)

    # Get all visible subfolders related to any of the folders on the path to
    # the root.
    all_folders = Folder.objects.for_user(user, VIEW) \
        .filter(parent_id__in=ancestor_ids).distinct()
    all_folders = {x.id: x for x in all_folders}

    # Include also the root. Not the best solution... Still, cached always.
    root = Folder.objects.get(parent__isnull=True)
    all_folders[root.id] = root

    visible_original_folder_ids = set()
    to_check = []
    for folder in folders:
        # WARNING: manually checking Folder permissions here!
        if folder.id in all_folders or not folder.hidden or folder.author == user:
            # OK, accessible
            # Use old instances where possible, as there is maybe some cached data.
            all_folders[folder.id] = folder
            visible_original_folder_ids.add(folder.id)
        else:
            # still not sure
            to_check.append(folder.id)

    if to_check:
        # NOTE: .hidden and .author permission is already checked.
        queryset = get_object_ids_with_exclusive_permission(user, VIEW,
            model=Folder, filter_ids=to_check)
        visible_original_folder_ids |= set(queryset)

    # Check permission for original folders
    for folder in folders:
        # Check if this (main) folder is accessible / visible
        chain_ids = [int(x) for x in folder.cache_ancestor_ids.split(',') if x]

        # To have access to the folder, user has to have permission to view
        # the folder itself and *all of its ancestors*.
        if folder.id not in visible_original_folder_ids \
                or not all(x in all_folders for x in chain_ids):
            # Not visible, remove it from menu tree! I.e. do not just remove
            # the original folder, remove whole chain to the root. (that's why
            # we need the counter here)
            ancestor_counter.subtract(chain_ids)

    # Map folders to their parents
    folder_children = defaultdict(list)
    for x in all_folders.itervalues():
        # Ignore inaccessible folders. None means it is not an ancestor, 0
        # means no access.
        if ancestor_counter.get(x.id) is not 0:
            folder_children[x.parent_id].append(x)

    try:
        # Root folder is None's only subfolder.
        root = folder_children[None][0]
    except IndexError:
        # No access to root, i.e. no access to any of the original folders.
        return None # Bye

    # Generate folder tree. This is probably the best way to
    #   1) Ignore inaccessible folders
    #   2) Sort folders, i.e. show in right order
    stack = [root]
    sorted_folders = []
    while len(stack):
        folder = stack.pop()
        if folder.parent_id:
            folder._depth = all_folders[folder.parent_id]._depth + 1
            sorted_folders.append(folder)   # root not in sorted folders!
        else:
            folder._depth = 0   # root

        children = folder_children[folder.id]

        # Sort by parent_index in reverse order (note that we are using LIFO)!.
        stack.extend(sorted(children, key=lambda x: -x.parent_index))

    # Get user's solution statuses.
    user_stats = Folder.many_get_user_stats(sorted_folders, user)

    # Finally, generate menu HTML
    menu = [x._html_menu_item(user, x.id in ancestor_ids, x._depth,
        user_stats.get(x.id)) for x in sorted_folders]

    return {
        'folder_children': folder_children,
        'folder_tree': u''.join(menu),
#        'sorted_folders': sorted_folders, # Not used currently. Enable if needed.
    }


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
