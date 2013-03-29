from django.db import models
from django.db.models import Q
from django.contrib.contenttypes import generic
from django.template.defaultfilters import slugify

from tags.managers import TaggableManager

from permissions.constants import VIEW
from permissions.models import ObjectPermission
from permissions.utils import has_group_perm
from task.models import Task
from search.utils import search_tasks
from skoljka.utils.tags import tag_list_to_html
from skoljka.utils.string_operations import list_strip

import itertools

# TODO: hm, DRY? ovo se ponavlja i u task
class FolderManager(models.Manager):
    def for_user(self, user, permission_type):
        if user is not None and user.is_authenticated():
            q = Q(permissions__group__user=user,
                permissions__permission_type=permission_type)
            if permission_type == VIEW:
                q |= Q(hidden=False)
            return self.filter(q)
        elif permission_type == VIEW:
            return self.filter(hidden=False)
        else:
            return self.none()


class Folder(models.Model):
    class Meta:
        permissions = (("can_publish_folders", "Can publish folders"), )

    name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=64)
    parent = models.ForeignKey('self', blank=True, null=True)
    parent_index = models.IntegerField(default=0)
    tag_filter = models.CharField(max_length=256, blank=True)

    # Folder Collection
    structure = models.TextField(blank=True)

    # Cache
    # e.g. '', 'category/', 'category/geometry/'
    cache_path = models.CharField(max_length=1000, blank=True, db_index=True)
    cache_ancestor_ids = models.CharField(max_length=255, blank=True)

    hidden = models.BooleanField(default=False)
    permissions = generic.GenericRelation(ObjectPermission)

    tasks = models.ManyToManyField(Task, blank=True)
    objects = FolderManager();

    def __unicode__(self):
        return "%s - [%s]" % (self.name, self.tag_filter)

    def get_absolute_url(self):
        # TODO: add id to URL -- '/folder/<id>/<path>/' -- to be able to use
        # old urls (in case the folder is moved somewhere)
        return '/folder/' + self.cache_path

    def has_perm(self, user, type):
        return user.is_staff or has_group_perm(user, self, type)

    @staticmethod
    def _html_breadcrumb_item(name, path):
        return u'<li><a href="/folder/%s">%s</a></li>' % (path, name)

    @staticmethod
    def _html_menu_item(name, path, depth):
        return u'<div style="padding-left:%dpx">&raquo; '   \
            '<a href="/folder/%s">%s</a></div>\n' % ((depth - 1) * 10, path, name)

    def tag_list_html(self):
        return tag_list_to_html(self.tag_filter)

    @staticmethod
    def _parse_child(child):
        """
            Parse child info. For structured / virtual folders only.
        """
        T = list_strip(child.split('/'), remove_empty=False)
        if len(T) == 1:
            data = [T[0], tag_list_to_html(T[0]), T[0], slugify(T[0])]
        elif len(T) == 2:
            data = [T[0], tag_list_to_html(T[1]), T[1], slugify(T[0])]
        else:
            data = [T[0], tag_list_to_html(T[1]), T[1], slugify(T[2])]
        return dict(zip(['name', 'tag_list_html', 'tags', 'slug'], data))

    def get_template_data_from_path(self, path, user):
        # For folders with additional structure, path must start with cache_path
        # but for folders without structure, paths must be equal
        if self.structure and not path.startswith(self.cache_path) \
                or not self.structure and path != self.cache_path:
            print bool(self.structure), self.cache_path, path
            return None

        ###############################
        # Prepare folder information
        ###############################

        chain_ids = [int(x) for x in self.cache_ancestor_ids.split(',') if x]
        chain = Folder.objects.in_bulk(chain_ids)

        chain_ids.append(self.id)
        chain[self.id] = self       # manually add self

        # Get all visible subfolders related to current chain.
        all_children = list(Folder.objects.for_user(user, VIEW) \
            .filter(parent_id__in=chain_ids).distinct())

        for folder in all_children:
            # chain
            ch_ids = [int(x) for x in folder.cache_ancestor_ids.split(',') if x]

            folder._depth = len(ch_ids)
            folder._multiindex = [chain[id].parent_index for id in ch_ids]
            folder._multiindex.append(folder.parent_index)

        # check permission for current folder
        subfolder_ids = set((subfolder.id for subfolder in all_children))
        for folder in chain.itervalues():
            if folder.parent_id is not None and folder.id not in subfolder_ids:
                return None

        # menu tree order
        all_children.sort(key=lambda x: x._multiindex)


        # Virtual / structured folders?
        if self.structure:
            subdata = self._get_template_data_from_path__collection(path, user)
            if not subdata:
                return None
        else:
            subdata = {}

        # list of all tags; whole chain including virtual folders
        tag_list = itertools.chain(subdata.get('tag_list', []),
            *[x.tag_filter.split(',') for x in chain.itervalues()])
        tag_list = set(filter(None, tag_list))    # remove duplicates

        # Check if there is any tag filter to cancel. Tag "xyz" will be
        # removed if there is another tag "~xyz" in the list.
        # For example, a folder has "geo" tag, but some of its subfolders
        # wants to disable it for some reason, then the subfolder can have
        # "~geo" as one of its filter tags.

        # Please note that ~ is not the same as -, because - is reserved for
        # eventual (?) advanced search.
        to_remove = []
        for tag in tag_list:
            if tag[0] == '~':
                to_remove.append(tag)
                to_remove.append(tag[1:])

        # remove, and finally convert back to list
        tag_list -= set(to_remove)
        tag_list = list(tag_list)

        if tag_list:
            tasks = search_tasks(tags=tag_list, user=user, show_hidden=True)
        else:
            tasks = self.tasks.all()


        ###############################
        # Generate HTML code
        ###############################

        # Manually insert virtual subfolders in the middle of menu
        menu = []
        for x in all_children:
            menu.append(Folder._html_menu_item(x.name, x.cache_path, x._depth))
            if x.id == self.id:
                menu.extend(subdata.get('menu', []))

        # Merge real chain and virtual
        breadcrumb = [Folder._html_breadcrumb_item(chain[id].name,
            chain[id].cache_path) for id in chain_ids]
        breadcrumb.extend(subdata.get('breadcrumb', []))

        # If current folder has some subfolders, then show "Select subcategory"
        # message in the case tasks queryset is empty. If there is no
        # subfolders, show "Folder empty" message.
        has_subfolders = subdata.get('has_subfolders') \
            or any((x.parent_id == self.id for x in all_children))
        data = {
            'menu_folder_tree': u''.join(menu),
            'tasks': tasks,
            'breadcrumb': u' &raquo; '.join(breadcrumb),
            'tag_list': tag_list,
            'tag_list_html': tag_list_to_html(tag_list),
            'has_subfolders': has_subfolders,
        }

        # if not virtual and no tag filters
        if self.cache_path == path:
            data['folder'] = self

        return data


    # Folder Collection
    #TODO(ikicic): uljepsati i pojasniti kod
    #TODO: optimizirati! (mozda i serializirati za sql)
    def _get_template_data_from_path__collection(self, path, user):
        # Note that it is not possible to set permissions for virtual folders.

        structure = []
        for G in list_strip(self.structure.split('@')):
            levels = []
            for L in list_strip(G.split('|')):
                levels.append([Folder._parse_child(C) for C in list_strip(L.split(';'))])
            structure.append(levels)

        depth = self.cache_path.count('/')
        P = filter(None, path[len(self.cache_path):].split('/'))

        print depth, P

        has_subfolders = False
        tree = []
        tag_list = []
        breadcrumb = []
        any = False
        for G in structure:         # for each group
            k = 0
            current_path = self.cache_path
            tree_end = []

            # k == len(P) is hack
            while k <= len(P) and k < len(G):    # levels
                next = None
                tree_end2 = []
                for C in G[k]:                  # for each child
                    menu_item = Folder._html_menu_item(C['name'],
                        '%s%s/' % (current_path, C['slug']), k + depth + 1)
                    if next is None:
                        tree.append(menu_item)
                        if k < len(P) and P[k] == C['slug']:
                            next = C
                    else:
                        tree_end2.append(menu_item)
                tree_end = tree_end2 + tree_end

                if next is None:
                    break
                else:
                    k += 1
                    current_path += next['slug'] + '/'
                    tag_list.extend(next['tags'].split(','))
                    breadcrumb.append(Folder._html_breadcrumb_item(next['name'], path))
            tree.extend(tree_end)

            if k == len(P):     # k will never be greater than len(P)
                if k < len(G):
                    has_subfolders = True
                any = True      # url is ok

        if not any:
            return None         # url is not ok

        print 'has_subfolders', has_subfolders, path
        return {
            'tag_list': tag_list,
            'breadcrumb': breadcrumb,
            'menu': tree,
            'has_subfolders': has_subfolders,
        }

