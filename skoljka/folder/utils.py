from collections import Counter, defaultdict

from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Max
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from skoljka.folder.models import (
    FOLDER_NAMESPACE_FORMAT,
    FOLDER_NAMESPACE_FORMAT_ID,
    Folder,
    FolderTask,
)
from skoljka.permissions.constants import VIEW
from skoljka.permissions.signals import objectpermissions_changed
from skoljka.permissions.utils import get_object_ids_with_exclusive_permission
from skoljka.search.models import SearchCacheElement
from skoljka.search.utils import reverse_search, search
from skoljka.solution.models import Solution
from skoljka.tags.signals import object_tag_ids_changed
from skoljka.tags.utils import get_object_tagged_items
from skoljka.task.models import Task
from skoljka.usergroup.models import UserGroup
from skoljka.utils import ncache
from skoljka.utils.string_operations import slugify


def add_or_remove_folder_task(folder_id, task_id, add):
    """Add or remove given task from the given folder."""
    try:
        foldertask = FolderTask.objects.get(folder_id=folder_id, task_id=task_id)
    except FolderTask.DoesNotExist:
        foldertask = None

    if foldertask and not add:
        foldertask.delete()
        changed = True
    elif not foldertask and add:
        info = FolderTask.objects.filter(folder_id=folder_id).aggregate(
            Max('position'), Count('id')
        )
        position = max(info['position__max'], info['id__count']) + 1
        FolderTask.objects.create(
            folder_id=folder_id, task_id=task_id, position=position
        )
        changed = True
    else:
        changed = False

    if changed:
        ncache.invalidate_namespace(FOLDER_NAMESPACE_FORMAT_ID.format(folder_id))


def get_folder_descendant_ids(folder_id):
    """
    Given a folder ID, returns the list of IDs of all of its descendants.
    """

    result = []
    last_level = [folder_id]
    while last_level:
        last_level = Folder.objects.filter(parent_id__in=last_level).values_list(
            'id', flat=True
        )
        result.extend(last_level)

    return result


def get_task_folder_ids(task):
    """
    Returns the list of IDs of all folders containing given task.
    Combines result of many-to-many relation and folder-filters.

    Does not check permissions, and not supposed to do any checks.

    Note that even search results are copied into FolderTask for
    folder-filters, there may still be some of those Folders whose m2m is not
    refreshed (i.e. their .cache_searchcache is None).
    """
    # Implementation of permission check is very complicated, do not implement
    # it here! Use get_visible_folder_tree instead.

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
        search_ids = SearchCacheElement.objects.filter(
            cache=search_cache, content_type=content_type
        ).values_list('object_id', flat=True)
    else:
        search_ids = []

    ids = list(m2m_ids) + list(search_ids)

    # Remove duplicates (does not preserve order)
    return list(set(ids))


def get_visible_folder_tree(folders, user, exclude_subtree=None):
    """
    Get whole visible folder tree containing selected folders.

    To remove a subtree of a specific folder, use exclude_subtree.
        exclude_subtree = xyz would skip xyz's subtree, but it would
        leave xyz itself.

    Also returns some other useful data.
    Fills returned folder instances with ._depth.
    """

    # Pick all ancestors, together with the original folders. Used for
    # permission check.
    ancestor_ids = sum([x.cache_ancestor_ids.split(',') for x in folders], [])
    ancestor_ids = [int(x) for x in ancestor_ids if x]
    ancestor_ids.extend([x.id for x in folders])
    ancestor_counter = Counter(ancestor_ids)

    # Now remove duplicates
    ancestor_ids = set(ancestor_ids)

    # Get all visible subfolders related to any of the folders on the path to
    # the root.
    all_folders = (
        Folder.objects.for_user(user, VIEW)
        .filter(parent_id__in=ancestor_ids)
        .distinct()
    )
    all_folders = {x.id: x for x in all_folders}

    # Include also the root. Not the best solution... Still, cached always.
    root = Folder.objects.get(parent__isnull=True)
    all_folders[root.id] = root

    visible_original_folder_ids = set()
    to_check = []
    for folder in folders:
        # WARNING: manually checking Folder permissions here!
        if folder.id in all_folders or not folder.hidden or folder.author == user:
            # OK, accessible. Use old instances where possible, as there is
            # maybe some cached data.
            all_folders[folder.id] = folder
            visible_original_folder_ids.add(folder.id)
        else:
            # still not sure
            to_check.append(folder.id)

    if to_check:
        # NOTE: .hidden and .author permission is already checked.
        queryset = get_object_ids_with_exclusive_permission(
            user, VIEW, model=Folder, filter_ids=to_check
        )
        visible_original_folder_ids |= set(queryset)

    # Check permission for original folders
    for folder in folders:
        # Check if this (main) folder is accessible / visible
        chain_ids = [int(x) for x in folder.cache_ancestor_ids.split(',') if x]

        # To have access to the folder, user has to have permission to view the
        # folder itself and *all of its ancestors*.
        if folder.id not in visible_original_folder_ids or not all(
            x in all_folders for x in chain_ids
        ):
            # Not visible, remove it from menu tree! I.e. do not just remove
            # the original folder, remove whole chain to the root. (that's why
            # we need the counter here)
            ancestor_counter.subtract(chain_ids)
            ancestor_counter.subtract([folder.id])

    # Map folders to their parents
    folder_children = defaultdict(list)
    for x in all_folders.itervalues():
        # Ignore inaccessible folders. None means it is not an ancestor, 0
        # means no access.
        if ancestor_counter.get(x.id) != 0:
            folder_children[x.parent_id].append(x)

    try:
        # Root folder is None's only subfolder.
        root = folder_children[None][0]
    except IndexError:
        # No access to root, i.e. no access to any of the original folders.
        return None  # Bye

    # Generate folder tree. This is probably the best way to
    #   1) Ignore inaccessible folders
    #   2) Sort folders, i.e. show in right order
    stack = [root]
    sorted_folders = []
    while len(stack):
        folder = stack.pop()
        if folder.parent_id:
            folder._depth = all_folders[folder.parent_id]._depth + 1
            sorted_folders.append(folder)  # root not in sorted folders!
        else:
            folder._depth = 0  # root

        if not exclude_subtree or exclude_subtree.id != folder.id:
            children = folder_children[folder.id]

            # Sort by parent_index in reverse order (note that we are using
            # LIFO)!.
            stack.extend(sorted(children, key=lambda x: -x.parent_index))

    return {
        'ancestor_ids': ancestor_ids,
        'folder_children': folder_children,
        'sorted_folders': sorted_folders,
    }


def prepare_folder_menu(folders, user):
    """
    Given list of folders, prepare folder menu showing all those folders
    at once. Ignores from input all folder inaccessible for the given user.

    Returns dict with following keys:
        folder_children - dictionary {folder.id: list of children instances}
        folder_tree - HTML of folder tree
    """
    # Note: This method calls Folder.many_get_user_stats, which makes it
    # sometimes very slow. Actually, the method is relatively fast. Still, more
    # optimizations are welcome here, because this method is called on almost
    # every request...

    data = get_visible_folder_tree(folders, user)

    if not data:
        return {'folder_children': {}, 'folder_tree': u''}

    ancestor_ids = data['ancestor_ids']
    folder_children = data['folder_children']
    sorted_folders = data['sorted_folders']

    # Get user's solution statuses.
    user_stats = Folder.many_get_user_stats(sorted_folders, user)

    # Finally, generate menu HTML
    menu = [
        x._html_menu_item(x.id in ancestor_ids, x._depth, user_stats.get(x.id))
        for x in sorted_folders
    ]

    return {
        'folder_children': folder_children,
        'folder_tree': u''.join(menu),
        #        'sorted_folders': sorted_folders, # Not used currently. Enable if needed.
    }


class FolderInfo:
    """
    Helper struct used in refresh_path_cache.
    """

    def __init__(self, id, short_name):
        self.id = id
        self.parent = None
        self.short_name = short_name

        self.ancestors = None
        self.path = None

    def __repr__(self):
        return '#{} {}'.format(self.id, getattr(self.parent, 'id', None))

    def recursion(self, folders):
        if self.ancestors is not None:
            return  # already done

        if self.parent is None:  # if root
            self.ancestors = ''
            self.path = ''
        else:
            if self.parent.ancestors is None:
                self.parent.recursion(folders)

            self.ancestors = self.parent.ancestors + str(self.parent.id) + ','
            self.path = self.parent.path + slugify(self.short_name) + '/'


def refresh_path_cache(queryset):
    """
    Refresh folder path cache information as
        cache_ancestor_ids, cache_path.

    When updating folder hierarchy, please refresh all necessary folders.
    *For each selected folder, all of its ancestor must also be selected!*
    """
    folder_list = queryset.values_list('id', 'parent_id', 'short_name')

    folders = {
        id: FolderInfo(id, short_name) for (id, parent_id, short_name) in folder_list
    }

    for id, parent_id, short_name in folder_list:
        folders[id].parent = parent_id and folders[parent_id]

    for f in folders.itervalues():
        f.recursion(folders)

    for id, f in folders.iteritems():
        Folder.objects.filter(id=id).update(
            cache_ancestor_ids=f.ancestors[:-1], cache_path=f.path
        )


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
    # One could replace .task with .task_id, but the problem is with the
    # methods get_task_folder_ids is using.
    invalidate_cache_for_folder_ids(get_task_folder_ids(task))


@receiver(objectpermissions_changed, sender=Folder)
def _invalidate_on_folder_permissions_update(sender, **kwargs):
    # Invalidate itself.
    namespace = FOLDER_NAMESPACE_FORMAT.format(kwargs['instance'])
    ncache.invalidate_namespace(namespace)


@receiver(post_save, sender=Solution)
def _invalidate_on_solution_update(sender, **kwargs):
    instance = kwargs['instance']
    if instance._original_detailed_status != instance.detailed_status:
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
    folder_ids = (
        Folder.objects.filter(
            hidden=True, objpermissions__group_id=kwargs['instance'].group_id
        )
        .values_list('id', flat=True)
        .distinct()
    )
    invalidate_cache_for_folder_ids(folder_ids)


@receiver(object_tag_ids_changed, sender=Task)
def _invalidate_on_task_tags_change(sender, old_tag_ids, new_tag_ids, **kwargs):
    content_type = ContentType.objects.get_for_model(Folder)

    # TODO: Optimize. Filter only those folders that really need invalidation...
    search_cache_ids = []
    diff = set(old_tag_ids) ^ set(new_tag_ids)
    for tag in diff:
        search_cache = search(tag_ids=[tag])
        search_cache_ids.append(search_cache.id)

    folder_ids = SearchCacheElement.objects.filter(
        cache_id__in=search_cache_ids, content_type=content_type
    )
    folder_ids = list(set(folder_ids.values_list('object_id', flat=True)))

    FolderTask.objects.filter(folder_id__in=folder_ids).delete()
    invalidate_cache_for_folder_ids(folder_ids)


@receiver(object_tag_ids_changed, sender=Folder)
def _refresh_cache_tags_on_tags_change(sender, instance, **kwargs):
    instance.refresh_cache_tags()
