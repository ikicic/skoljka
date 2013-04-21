from django.db import models
from django.db.models import Count
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.generic import GenericRelation
from django.core.cache import cache

from permissions.constants import VIEW
from permissions.models import PermissionsModel
from tags.managers import TaggableManager
from task.models import Task
from search.models import SearchCacheElement
from search.utils import search_tasks
from solution.models import Solution, DETAILED_STATUS
from tags.managers import TaggableManager
from skoljka.utils import interpolate_three_colors, ncache
from skoljka.utils.decorators import cache_function
from skoljka.utils.tags import tag_list_to_html
from skoljka.utils.string_operations import slugify

import itertools, time

FOLDER_TASKS_DB_TABLE = 'folder_folder_tasks'

FOLDER_USER_CACHE_KEY = 'fo%du%d'

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

    # Take care of cache_tags if updating tags!
    tags = TaggableManager(blank=True)

    # Cache, comma-separated sorted list of tags.
    cache_tags = models.CharField(max_length=256, blank=True)

    # Cache, comma-separated list of ancestors, from the root to the parent
    cache_ancestor_ids = models.CharField(max_length=255, blank=True)

    tasks = models.ManyToManyField(Task, blank=True, through='FolderTask')
    search_cache_elements = GenericRelation(SearchCacheElement)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return '/folder/{}/{}'.format(self.id, slugify(self.name))

    def _refresh_cache_tags(self, commit=True):
        self.cache_tags = ','.join(
            self.tags.order_by('name').values_list('name', flat=True))
        if commit:
            self.save()

    def _html_breadcrumb_item(self):
        return u'<li><a href="{}">{}</a></li>'.format(self.get_absolute_url(),
            self.name)

    def _should_show_stats(self):
        """
            Show solutions statistics only if year-folder (or similar).
        """
        return self.short_name.isdigit()

    def _html_menu_item(self, user, is_open, depth, S):
        """
            Parameters:
                is_open - is folder open (is in chain?)
                user - request.user
                depth - folder depth
                S - solution_stats (abbr.)
        """

        cls = 'nav-folder-hidden' if self.hidden else 'nav-folder'
        if is_open:
            cls += ' nav-folder-open'

        data_attr = ''
        stats = ''
        if self._should_show_stats() and S and sum(S) - S[DETAILED_STATUS['blank']] > 0:
            total = self.get_user_visible_task_count(user)
            solved = S[DETAILED_STATUS['as_solved']]        \
                + S[DETAILED_STATUS['submitted_not_rated']] \
                + S[DETAILED_STATUS['solved']]

            todo = S[DETAILED_STATUS['todo']]

            percent = float(solved) / total
            todo_percent = float(todo) / total
            if S[DETAILED_STATUS['wrong']]:
                r, g, b = 255, 0, 0
            else:
                r, g, b = interpolate_three_colors(200, 200, 200,
                    100, 200, 100, percent, 230, 180, 92, todo_percent)

            stats = '<span style="color:#%02X%02X%02X;">(%d%%)</span>' \
                % (r, g, b, 100 * percent)
            data_attr = ' data-task-count="%d" data-sol-stats="%s"' \
                % (total, ','.join([str(x) for x in S]))

        return u'<li class="%s" style="margin-left:%dpx;"> '   \
            '<a href="%s"%s>%s %s</a></li>\n' % (cls, depth * 10 - 7,
            self.get_absolute_url(), data_attr, self.short_name, stats)

    def tag_list_html(self):
        return tag_list_to_html(self.cache_tags)


    def get_queryset(self, user, no_perm_check=False, order=True):
        """
            Depending on type of folder (tag filter / manual), return
            queryset of contained Tasks.

            Flags (useful for optimization purposes):
                no_perm_check - do not check permission, return all tasks
                order - order by default order (if defined)
        """

        # If we know there is no hidden task, don't check for them.
        # Note: check if no_perm_check is False before calling this method!
        if not no_perm_check and not self.has_any_hidden_task():
            no_perm_check = True

        if self.cache_tags:
            return search_tasks(tags=self.cache_tags, user=user,
                show_hidden=True, no_hidden_check=no_perm_check)
        else:
            if no_perm_check:
                tasks = self.tasks.for_user(user, VIEW).distinct()
            else:
                tasks = self.tasks

            return tasks.order_by('foldertask__position') if order else tasks
            #  .extra(select={'position': FOLDER_TASKS_DB_TABLE + '.position'}, order_by=['position'])

    @cache_function(namespace_format='Folder{0.pk}')
    def has_any_hidden_task(self):
        # No danger from infinite recursion here.
        return self.get_queryset(None, no_perm_check=True, order=False) \
            .filter(hidden=True).exists()

    @cache_function(namespace_format='Folder{0.pk}')
    def get_user_visible_task_count(self, user):
        return self.get_queryset(user, order=False).count()

    def _get_user_solution_stats(self, user):
        """
            Returns user solutions statistics.

            Currently, returns list with a number of solution with specific
            detailed status, one element for each status.

            For more info on detailed status, look at
            Solution.get_detailed_status().
        """
        # Get all the tasks in this folder.
        # Ignore permissions. If an user solved a problem, he/she probably
        # has the permission to view it. Ignore abnormal cases.
        tasks = self.get_queryset(user, no_perm_check=True, order=False)

        # TODO: Optimize! Note that we don't need the Task table itself, and
        #   that __in is also not the perfect solution.
        # If Solution.detailed_status is added, one can use Count here...
        solutions = Solution.objects.filter(author=user, task__in=tasks) \
            .only('status', 'correctness_avg')

        # Count how many solutions with specific detailed status...
        result = [0] * len(DETAILED_STATUS)
        for x in solutions:
            result[x.get_detailed_status()] += 1

        return result

    @staticmethod
    def many_get_user_solution_stats(folders, user):
        """
            Get user statistics for multiple folders.
            Cache wrapper around _get_user_solution_stats.

            Returns dictionary id -> stats.
        """
        # TODO: Optimize this query. For example, it is probably much much
        # faster to take all the solutions, all related tasks (or the union of
        # all folders, and then related solutions) and manually generate
        # the result.

        if not user.is_authenticated():
            return {}

        start_time = time.time()

        namespaces = ['Folder{0.pk}'.format(x) for x in folders]
        keys = ['User{}'.format(user.id)] * len(namespaces)
        cached, full_keys = ncache.get_many_for_update(namespaces, keys)

        # Most common case, check immediately:
        if len(keys) == len(cached):
            return {x.id: cached[full_key]
                for x, full_key in zip(folders, full_keys)}

        result = {}

        # Check for values not found in cache
        to_save = {}
        for x, full_key in zip(folders, full_keys):
            if full_key in cached:
                result[x.id] = cached[full_key]
            else:
                value = x._get_user_solution_stats(user)
                to_save[full_key] = value
                result[x.id] = value

        cache.set_many(to_save)

        print 'user solution stats for %d folders found in %lfs' % (len(to_save), time.time() - start_time)
        return result


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

            # Get user's solution statuses.
            solution_stats = Folder.many_get_user_solution_stats(all_children, user)

            menu = [x._html_menu_item(user, x.id in chain_ids, x._depth,
                solution_stats.get(x.id)) for x in all_children]
            data['menu_folder_tree'] = u''.join(menu)

            # If current folder has some subfolders, then show
            # "Select subcategory" message in the case tasks queryset is empty.
            # If there is no subfolders, show "Folder empty" message.
            data['has_subfolders'] = \
                any((x.parent_id == self.id for x in all_children))

        if Folder.DATA_DETAILS in flags:
            #------ HTML ------#

            data['tasks'] = self.get_queryset(user)
            data['tag_list'] = self.cache_tags
            data['tag_list_html'] = tag_list_to_html(self.cache_tags)

        # Other data

        data['folder'] = self

        return data


class FolderTask(models.Model):
    class Meta:
        db_table = FOLDER_TASKS_DB_TABLE

    folder = models.ForeignKey(Folder)
    task = models.ForeignKey(Task)
    position = models.IntegerField(default=0)
