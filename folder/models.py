from django.db import connection, models, transaction
from django.db.models import Count
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.generic import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache

import johnny.cache

from permissions.constants import VIEW
from permissions.models import BasePermissionsModel
from permissions.utils import get_object_ids_with_exclusive_permission
from tags.managers import TaggableManager
from task.models import Task
from search.models import SearchCache, SearchCacheElement
from search.utils import search, search_tasks
from solution.models import Solution, DETAILED_STATUS
from tags.managers import TaggableManager
from skoljka.utils import interpolate_three_colors, ncache
from skoljka.utils.decorators import cache_function, cache_many_function
from skoljka.utils.models import icon_help_text
from skoljka.utils.tags import tag_list_to_html

import itertools, time

FOLDER_TASKS_DB_TABLE = 'folder_folder_tasks'

FOLDER_NAMESPACE_FORMAT = 'Folder{0.pk}'
FOLDER_NAMESPACE_FORMAT_ID = 'Folder{}'

IN_OUT_OFFSET = 12
# The difference between 'inside' and 'outside' for list-style.
# Look at folder.css for more info.

class Folder(BasePermissionsModel):
    class Meta:
        permissions = (
            ("can_publish_folders", "Can publish folders"),
            ("can_set_short_name", "Can set short name"),
            ("advanced_create", "Advanced folder create"),
        )

    name = models.CharField(max_length=64, verbose_name='Ime')      # full name
    short_name = models.CharField(max_length=128, verbose_name='Kratko ime',
        help_text=icon_help_text(u'Ime prikazano u izborniku. Ukoliko se ne '
            u'razlikuje od punog imena, možete ostaviti prazno.'))   # menu name

    # PermissionsModel
    hidden = models.BooleanField(default=True, verbose_name='Skriveno') # default True!
    author = models.ForeignKey(User)

    # Sometimes there is no particular reason to edit a folder. (e.g. year
    # subfolders of some competition folder) Therefore, to keep it clean,
    # it is possible to make editing unavailable.
    # All folders generated with advanced_add are uneditable by default.
    editable = models.BooleanField(default=True)

    parent = models.ForeignKey('self', blank=True, null=True)
    parent_index = models.IntegerField(default=0)

    # Take care of cache_tags if updating tags!
    tags = TaggableManager(blank=True)

    # Cache, comma-separated sorted list of tags, both names and IDs.
    cache_tags = models.CharField(max_length=256, blank=True)
    cache_tag_ids = models.CharField(max_length=255, blank=True)

    # Cache, comma-separated list of ancestors, from the root to the parent
    cache_ancestor_ids = models.CharField(max_length=255, blank=True)

    # Cache, full path, used in URLs. E.g. '', 'dir/', 'dir/subdir/'
    cache_path = models.CharField(max_length=1000, blank=True, db_index=True)

    # Cache, link to SearchCache instance, in the case of a folder-filter type
    cache_searchcache = models.ForeignKey(SearchCache, blank=True, null=True,
        on_delete=models.SET_NULL) # WARNING: Do not remove SET_NULL!!

    tasks = models.ManyToManyField(Task, blank=True, through='FolderTask')
    search_cache_elements = GenericRelation(SearchCacheElement)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        #return '/folder/{}/{}'.format(self.id, slugify(self.name))
        return '/folder/{}/{}'.format(self.id, self.cache_path)

    def _refresh_cache_tags(self, commit=True):
        old = self.cache_tags

        tags = self.tags.order_by('name').values_list('id', 'name')
        if tags:
            ids, names = zip(*tags)
        else:
            ids = names = []

        self.cache_tags = ','.join(names)
        self.cache_tag_ids = ','.join(str(id) for id in ids)

        # Should invalidate folder cache?
        if old != self.cache_tags:
            ncache.invalidate_namespace(FOLDER_NAMESPACE_FORMAT.format(self))
            self.cache_searchcache = None

        if commit:
            self.save()

    def _html_breadcrumb_item(self):
        return u'<li><a href="{}">{}</a></li>'.format(self.get_absolute_url(),
            self.name)

    @staticmethod
    def parse_solution_stats(S, total_solvable_count):
        """
            S = Solution statistics (list of counters, one for each detailed status)
            total_solvable_count = Number of solvable tasks in the folder

            Returns tuple:
                - bool, has any non blank solution
                - bool, has any non rated solutions
                - float, percent solved
                - 3-tuple of floats, color RGB
        """
        if not S or sum(S) - S[DETAILED_STATUS['blank']] <= 0:
            return False, False, 0, (150, 150, 150)

        solved = S[DETAILED_STATUS['as_solved']]        \
            + S[DETAILED_STATUS['correct']]
        todo = S[DETAILED_STATUS['todo']]

        percent = float(solved) / total_solvable_count
        todo_percent = float(todo) / total_solvable_count
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

    def _html_menu_item(self, is_open, depth, stats, cls='', extra=''):
        """
            Parameters:
                is_open - is folder open (is in chain?)
                depth - folder depth
                stats - stats from many_get_user_stats
                cls - additional CSS class, optional
                extra - extra HTML added between <li> and <a>, optional
        """

        cls += ' nav-folder-hidden' if self.hidden else ' nav-folder'
        if is_open:
            cls += ' nav-folder-open'

        stats_str = ''
        if stats and self._should_show_stats():
            # Extract statistics
            total, total_solvable, S = stats

            any, any_non_rated, percent, (r, g, b) =    \
                Folder.parse_solution_stats(S, total_solvable)

            if any:
                # Show extra + sign if there are any non rated solutions.
                plus_sign = '+' if any_non_rated else ''

                stats_str = '<span style="color:#%02X%02X%02X;">(%s%d%%)</span>' \
                    % (r, g, b, plus_sign, 100 * percent)

        return u'<li class="%s" style="margin-left:%dpx;"> '   \
            '%s<a href="%s">%s %s</a></li>\n' % (cls,
            depth * 10 - 7 + IN_OUT_OFFSET, extra, self.get_absolute_url(),
            self.short_name, stats_str)

    def tag_list_html(self):
        return tag_list_to_html(self.cache_tags)

    @staticmethod
    def _prepare_folderfilters(folders):
        content_type_id = ContentType.objects.get_for_model(Task).id

        # Ignore non-filters and those who already have FolderTask prepared.
        folders = filter(
            lambda x: x.cache_tag_ids and x.cache_searchcache_id is None,
            folders)

        if not folders:
            return

        folder_ids = [x.id for x in folders]
        FolderTask.objects.filter(folder_id__in=folder_ids).delete()

        for folder in folders:
            tag_ids = [int(x) for x in folder.cache_tag_ids.split(',')]

            folder.cache_searchcache_id = search(tag_ids=tag_ids).id
            folder.save()   # Yes, send signals.

            query = 'INSERT INTO folder_folder_tasks (folder_id, task_id, position)' \
                    ' SELECT {}, SCE.object_id, SCE.object_id FROM search_searchcacheelement SCE'\
                    ' WHERE SCE.content_type_id = {} AND SCE.cache_id = {};'.format(
                        folder.id,
                        content_type_id,
                        folder.cache_searchcache_id
                    )

            cursor = connection.cursor()
            cursor.execute(query)

        transaction.commit_unless_managed()

        johnny.cache.invalidate('search_searchcacheelement', 'folder_folder',
            'folder_folder_tasks')

    def get_queryset(self, user, no_perm_check=False, order=True):
        """
            Depending on type of folder (tag filter / manual), return
            queryset of contained Tasks.

            Flags (useful for optimization purposes):
                no_perm_check - do not check permission, return all tasks
                order - order by default order (if defined)
        """

        # If we know there is no hidden task, don't check permissions.
        # Note: check if no_perm_check is False before calling this method!
        if not no_perm_check and not self.has_any_hidden_task():
            no_perm_check = True

        # Prepare FolderTask for this Folder (if it is a folder-filter)
        Folder._prepare_folderfilters([self])

        tasks = self.tasks
        if not no_perm_check:
            tasks = self.tasks.for_user(user, VIEW).distinct()

        return tasks.order_by('foldertask__position') if order else tasks

    @cache_function(namespace=FOLDER_NAMESPACE_FORMAT, key='AnyHidden')
    def has_any_hidden_task(self):
        # No danger from infinite recursion here.
        return self.get_queryset(None, no_perm_check=True, order=False) \
            .filter(hidden=True).exists()

    @staticmethod
    @cache_many_function(
        namespace_format=FOLDER_NAMESPACE_FORMAT,
        key_format='User{1.id}',
        pre_test=lambda folders, user: (user.is_authenticated(), {}),
    )
    def many_get_user_stats(folders, user):
        """
            Get user statistics and other information for multiple folders.

            If user not authenticated, returns empty dictionary.
            Otherwise, returns dictionary
                {folder.id: [visible task count, visible solvable task count,
                    solution_stats]}   (*)
            where solution_stats is a list of solution counters,
            one element for each detailed status. E.g.
                (50, [0, 3, 0, 1, 2 (...)])

            (*) For implementation reasons, it returns lists instead of tuples.
        """
        start_time = time.time()

        # Prepare folder-filters, i.e. FolderTasks for those folders
        Folder._prepare_folderfilters(folders)

        # Get all the tasks in these folders. Check for permission to get the
        # visible count immediately.
        folder_task_ids = {}

        # {folder_id: [visible task count, solution statistics]}
        result = {x.id: [0, 0, [0] * len(DETAILED_STATUS)] for x in folders}

        query = 'SELECT FT.folder_id, T.id, T.author_id, T.hidden, T.solvable, S.detailed_status FROM folder_folder_tasks FT'  \
            ' INNER JOIN task_task T ON (FT.task_id = T.id)'   \
            ' LEFT OUTER JOIN solution_solution S ON (S.task_id = T.id AND S.author_id = {})' \
            ' WHERE FT.folder_id IN ({});'.format(
                user.id,
                ','.join(str(x.id) for x in folders)
            )

        cursor = connection.cursor()
        cursor.execute(query)

        # Task whose permissions have to be checked explicitly.
        to_check = []
        db_result = list(cursor.fetchall())
        for folder_id, task_id, author_id, hidden, solvable, detailed_status in db_result:
            if hidden and author_id != user.id:
                to_check.append(task_id)

        # Filter only visible Tasks
        visible_tasks = set(get_object_ids_with_exclusive_permission(
            user, VIEW, model=Task, filter_ids=to_check))   \
            if to_check else set()

        # Fill statistics
        for folder_id, task_id, author_id, hidden, solvable, detailed_status in db_result:
            # Is Task visible?
            if not hidden or author_id == user.id or task_id in visible_tasks:
                ref = result[folder_id]
                ref[0] += 1                         # Total Task count
                if solvable:
                    ref[1] += 1                     # Total solvable Task count
                if detailed_status is not None:
                    ref[2][detailed_status] += 1    # Solution statistics

        print 'user solution stats for %d folders found in %lfs' % (len(folders), time.time() - start_time)
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
