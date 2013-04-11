from django.db import models
from django.contrib.contenttypes import generic

from tags.managers import TaggableManager

from permissions.constants import VIEW
from permissions.models import PermissionsModel
from task.models import Task
from search.utils import search_tasks
from skoljka.utils.tags import tag_list_to_html
from skoljka.utils.string_operations import slugify

import itertools

FOLDER_TASKS_DB_TABLE = 'folder_folder_tasks'

class Folder(PermissionsModel):
    class Meta:
        permissions = (
            ("can_publish_folders", "Can publish folders"),
            ("advanced_create", "Advanced folder create"),
        )

    # Constants / masks given to get_template_data(...)
    DATA_MENU = 1
    DATA_DETAILS = 2
    DATA_ALL = [DATA_MENU, DATA_DETAILS]

    name = models.CharField(max_length=64)          # full name (shown in URL)
    short_name = models.CharField(max_length=128)   # menu name

    # Sometimes there is no particular reason to edit a folder. (e.g. year
    # subfolders of some competition folder) Therefore, to keep it clean,
    # it is possible to make editing unavailable.
    # All folders generated with advanced_add are uneditable by default.
    editable = models.BooleanField(default=True)

    parent = models.ForeignKey('self', blank=True, null=True)
    parent_index = models.IntegerField(default=0)
    tag_filter = models.CharField(max_length=256, blank=True)

    # Cache
    cache_ancestor_ids = models.CharField(max_length=255, blank=True)

    tasks = models.ManyToManyField(Task, blank=True, through='FolderTask')

    def __unicode__(self):
        return u'%s - [%s]' % (self.name, self.tag_filter)

    def get_absolute_url(self):
        return '/folder/{}/{}'.format(self.id, slugify(self.name))

    def _html_breadcrumb_item(self):
        return u'<li><a href="{}">{}</a></li>'.format(self.get_absolute_url(),
            self.name)

    def _html_menu_item(self, user, depth):
        cls = 'nav-folder-hidden' if self.hidden else 'nav-folder'
        return u'<li class="%s" style="margin-left:%dpx;"> '   \
            '<a href="%s">%s</a></li>\n' % (cls, depth * 10 - 7,
            self.get_absolute_url(), self.short_name)

    def tag_list_html(self):
        return tag_list_to_html(self.tag_filter)

    def get_template_data(self, user, flags=DATA_ALL):
        """
            Returns a dictionary of folder information.
            Parameter flags defines which information will be retrieved.
            The type is either the list of flags or a single flag.

            Always
                folder - self

            Flag description:
            DATA_MENU:
                menu_folder_tree - menu HTML
                has_subfolders - bool, True if current folder has any subfolders

            DATA_DETAILS:
                tasks - queryset to folder's tasks
                breadcrumb - HTML for the path breadcrumb
                tag_list - list of tags
                tag_list_html - HTML version
        """

        # If only one flag given, convert to a list
        if isinstance(flags, int):
            flags = [flags]

        # Result
        data = {}

        chain_ids = [int(x) for x in self.cache_ancestor_ids.split(',') if x]
        chain = Folder.objects.in_bulk(chain_ids)

        chain_ids.append(self.id)
        chain[self.id] = self       # manually add self

        if Folder.DATA_MENU in flags:
            # Get all visible subfolders related to the current chain.
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

            #------ HTML ------#

            menu = [x._html_menu_item(user, x._depth) for x in all_children]
            data['menu_folder_tree'] = u''.join(menu)

            # If current folder has some subfolders, then show
            # "Select subcategory" message in the case tasks queryset is empty.
            # If there is no subfolders, show "Folder empty" message.
            data['has_subfolders'] = \
                any((x.parent_id == self.id for x in all_children))

        if Folder.DATA_DETAILS in flags:
            if self.tag_filter:
                tasks = search_tasks(tags=self.tag_filter, user=user,
                    show_hidden=True)
                foldertasks = None
            else:
                tasks = self.tasks.for_user(user, VIEW) \
                    .order_by('foldertask__position').distinct()
                #  .extra(select={'position': FOLDER_TASKS_DB_TABLE + '.position'}, order_by=['position'])


            #------ HTML ------#

            data['tasks'] = tasks
            data['tag_list'] = self.tag_filter
            data['tag_list_html'] = tag_list_to_html(self.tag_filter)

        # Other data

        data['folder'] = self

        return data


class FolderTask(models.Model):
    class Meta:
        db_table = FOLDER_TASKS_DB_TABLE

    folder = models.ForeignKey(Folder)
    task = models.ForeignKey(Task)
    position = models.IntegerField(default=0)
