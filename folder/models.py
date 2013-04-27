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
from search.utils import search, search_tasks
from solution.models import Solution, DETAILED_STATUS
from tags.managers import TaggableManager
from skoljka.utils import interpolate_three_colors, ncache
from skoljka.utils.decorators import cache_function
from skoljka.utils.tags import tag_list_to_html
from skoljka.utils.string_operations import slugify

import itertools, time

FOLDER_TASKS_DB_TABLE = 'folder_folder_tasks'

FOLDER_NAMESPACE_FORMAT = 'Folder{0.pk}'
FOLDER_NAMESPACE_FORMAT_ID = 'Folder{}'

class Folder(PermissionsModel):
    class Meta:
        permissions = (
            ("can_publish_folders", "Can publish folders"),
            ("advanced_create", "Advanced folder create"),
        )

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
        old = self.cache_tags
        self.cache_tags = ','.join(
            self.tags.order_by('name').values_list('name', flat=True))

        # Should invalidate folder cache?
        if old != self.cache_tags:
            ncache.invalidate_namespace(FOLDER_NAMESPACE_FORMAT.format(self))

        if commit:
            self.save()

    def _html_breadcrumb_item(self):
        return u'<li><a href="{}">{}</a></li>'.format(self.get_absolute_url(),
            self.name)

    @staticmethod
    def parse_solution_stats(S, total_task_count):
        """
            S = Solution statistics (list of counters, one for each detailed status)
            total_task_count = Total tasks in the folder

            Returns tuple:
                - bool, has any non blank solution
                - bool, has any non rated solutions
                - float, percent solved
                - 3-tuple of floats, color RGB
        """
        if not S or sum(S) - S[DETAILED_STATUS['blank']] <= 0:
            return False, False, 0, (180, 180, 180)

        solved = S[DETAILED_STATUS['as_solved']]        \
            + S[DETAILED_STATUS['correct']]
        todo = S[DETAILED_STATUS['todo']]

        percent = float(solved) / total_task_count
        todo_percent = float(todo) / total_task_count
        if S[DETAILED_STATUS['wrong']]:
            r, g, b = 255, 0, 0
        else:
            r, g, b = interpolate_three_colors(180, 180, 180,
                100, 220, 100, percent, 230, 180, 92, todo_percent)

        non_rated = bool(S[DETAILED_STATUS['submitted_not_rated']])
        return True, non_rated, percent, (r, g, b)

    def _should_show_stats(self):
        """
            Show solutions statistics only if year-folder (or similar).
        """
        return self.short_name.isdigit()

    def _html_menu_item(self, user, is_open, depth, stats):
        """
            Parameters:
                is_open - is folder open (is in chain?)
                user - request.user
                depth - folder depth
                stats - stats from _get_user_stats
        """

        cls = 'nav-folder-hidden' if self.hidden else 'nav-folder'
        if is_open:
            cls += ' nav-folder-open'

        data_attr = ''
        stats_str = ''
        if stats and self._should_show_stats():
            # Extract statistics
            total, S = stats

            any, any_non_rated, percent, (r, g, b) =    \
                Folder.parse_solution_stats(S, total)

            if any:
                # Show extra + sign if there are any non rated solutions.
                plus_sign = '+' if any_non_rated else ''

                stats_str = '<span style="color:#%02X%02X%02X;">(%s%d%%)</span>' \
                    % (r, g, b, plus_sign, 100 * percent)
                data_attr = ' data-task-count="%d" data-sol-stats="%s"' \
                    % (total, ','.join([str(x) for x in S]))

        return u'<li class="%s" style="margin-left:%dpx;"> '   \
            '<a href="%s"%s>%s %s</a></li>\n' % (cls, depth * 10 - 7,
            self.get_absolute_url(), data_attr, self.short_name, stats_str)

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

    @cache_function(namespace_format=FOLDER_NAMESPACE_FORMAT)
    def has_any_hidden_task(self):
        # No danger from infinite recursion here.
        return self.get_queryset(None, no_perm_check=True, order=False) \
            .filter(hidden=True).exists()

    def _get_user_stats(self, user):
        """
            Returns user solutions statistics and other information.

            Currently, returns pair (visible_task_count, solution_stats),
            where solution_stats is a list of solution counters,
            one element for each detailed status. E.g.
                (50, [0, 3, 0, 1, 2 (...)])

            For more info on detailed status, look at Solution.
        """
        # Get all the tasks in this folder. Check for permission to get the
        # visible count immediately.
        task_ids = self.get_queryset(user, order=False)    \
            .values_list('id', flat=True)
        task_ids = list(task_ids)

        # TODO: Optimize! __in is also not the perfect solution.
        # If Solution.detailed_status is added, one can use Count here...
        solutions = Solution.objects.filter(author=user, task_id__in=task_ids) \
            .only('status', 'correctness_avg')

        # Count how many solutions with specific detailed status...
        stats = [0] * len(DETAILED_STATUS)
        for x in solutions:
            stats[x.detailed_status] += 1

        return len(task_ids), stats

    @staticmethod
    def many_get_user_stats(folders, user):
        """
            Get user statistics and other information for multiple folders.
            Cache wrapper around _get_user_stats.

            If use not authenticated, returns empty dictionary.
            Otherwise, returns whatever dictionary
                {folder.id: folder._get_user_stats(user)}
        """
        # TODO: Optimize this query. For example, it is probably much much
        # faster to take all the solutions, all related tasks (or the union of
        # all folders, and then related solutions) and manually generate
        # the result.

        if not user.is_authenticated():
            return {}

        start_time = time.time()

        namespaces = [FOLDER_NAMESPACE_FORMAT.format(x) for x in folders]
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
                value = x._get_user_stats(user)
                to_save[full_key] = value
                result[x.id] = value

        cache.set_many(to_save)

        print 'user solution stats for %d folders found in %lfs' % (len(to_save), time.time() - start_time)
        return result


    def get_details(self, user):
        """
            Returns a dictionary of following folder information:
                folder - self
                tag_list - list of tags
                tag_list_html - HTML version
                tasks - queryset to folder's tasks
        """

        return {
            'folder': self,
            'tag_list': self.cache_tags,
            'tag_list_html': tag_list_to_html(self.cache_tags),
            'tasks': self.get_queryset(user),
        }


class FolderTask(models.Model):
    class Meta:
        db_table = FOLDER_TASKS_DB_TABLE

    folder = models.ForeignKey(Folder)
    task = models.ForeignKey(Task)
    position = models.IntegerField(default=0)
