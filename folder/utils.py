from folder.models import Folder

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

def refresh_cache(queryset):
    """
        Refresh folder cache information as
            cache_ancestor_ids.

        Although it is possible to select only a subset of folders,
        please select all folders when using this action.
    """
    # This code is a modification of the earlier one, where more info was
    # saved (cache_path).
    folder_list = queryset.values_list('id', 'parent_id')

    folders = {id: FolderInfo(id)
        for (id, parent_id) in folder_list}

    for id, parent_id in folder_list:
        folders[id].parent = parent_id and folders[parent_id]

    for f in folders.itervalues():
        f.recursion(folders)

    for id, f in folders.iteritems():
        Folder.objects.filter(id=id).update(cache_ancestor_ids=f.ancestors[:-1])
