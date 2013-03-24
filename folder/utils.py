from folder.models import Folder

class FolderInfo:
    """
        Helper struct used in refresh_path_cache.
    """
    def __init__(self, id, slug):
        self.id = id
        self.slug = slug
        self.parent = None

        self.path = None
        self.ancestors = None

    def __repr__(self):
        return '#{} {} {}'.format(self.id, getattr(self.parent, 'id', None), self.slug)

    def recursion(self, folders):
        if self.path is not None:
            return # already done

        if self.parent is None: # if root
            self.path = ''
            self.ancestors = ''
        else:
            if self.parent.path is None:
                self.parent.recursion(folders)

            self.path = self.parent.path + self.slug + '/'
            self.ancestors = self.parent.ancestors + str(self.parent.id) + ','

def refresh_cache(queryset):
    """
        Refresh folder cache information as
            cache_path and cache_ancestor_ids.

        Although it is possible to select only a subset of folders,
        please select all folders when using this action.
    """
    folder_list = queryset.values_list('id', 'slug', 'parent_id')

    folders = {id: FolderInfo(id, slug)
        for (id, slug, parent_id) in folder_list}

    for id, slug, parent_id in folder_list:
        folders[id].parent = parent_id and folders[parent_id]

    for f in folders.itervalues():
        f.recursion(folders)

    for id, f in folders.iteritems():
        print id, f.path, f.ancestors
        Folder.objects.filter(id=id).update(cache_path=f.path,
            cache_ancestor_ids=f.ancestors[:-1])
