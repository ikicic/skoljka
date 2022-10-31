import random

from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.generic import GenericRelation
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from skoljka.mathcontent.models import MathContent, Attachment
from skoljka.permissions.constants import EDIT, VIEW, VIEW_SOLUTIONS
from skoljka.permissions.models import BasePermissionsModel, convert_permission_names_to_values
from skoljka.post.generic import PostGenericRelation
from skoljka.rating.fields import RatingField
from skoljka.search.models import SearchCacheElement
from skoljka.tags.managers import TaggableManager
from skoljka.utils.models import icon_help_text
from skoljka.utils import xss


MAX_SIMILAR_TASKS = 20

# TODO: rename "name" to "title"

# Please note that 0th element stands for undefined.
QUALITY_RATING_ATTRS = {
    'range': 6,
    'titles': [u'Nepoznato', u'Loš. Dosadan.', u'Ima i boljih.',
        u'Dobar zadatak.', u'Jako dobar. Zanimljiv.',
        u'Izvrstan. Vrlo zanimljiv.'],
}

DIFFICULTY_RATING_ATTRS = {
    'range': 11,
    'titles': [u'Neodređeno', u'OŠ lakši', u'OŠ teži', u'SŠ lakši', u'SŠ teži',
        u'Srednje težine', u'Shortlist 1/2', u'Shortlist 3/4', u'Shortlist 5/6',
        u'Shortlist 7/8', u'Nerješiv'],
    'on_update': 'skoljka.userprofile.models.task_difficulty_on_update',
}


class TaskBulkTemplate(BasePermissionsModel):
    author = models.ForeignKey(User)
    hidden = models.BooleanField(default=False, verbose_name=_("Hidden"))
    date_created = models.DateTimeField(auto_now_add=True)
    last_edit_date = models.DateTimeField(auto_now=True)
    name = models.CharField(blank=True, max_length=100, verbose_name=_("Name"))
    source_code = models.TextField(max_length=100000)

    def __unicode__(self):
        return u"#{} {} ({})".format(self.id, self.name, self.date_created)



# ovdje ili u recommend?
class SimilarTask(models.Model):
    task = models.ForeignKey('Task', db_index=True, related_name='from')
    similar = models.ForeignKey('Task', db_index=True, related_name='to')
    score = models.FloatField(db_index=True)



class Task(BasePermissionsModel):
    # BasePermissionsModel setting:
    object_permissions = ['view', 'edit', 'edit_permissions', 'view_solutions']

    # napomena: cache za Solution POST_SEND activity ovisi o ovom max_length, nemojte previse povecavati
    name = models.CharField(max_length=120, verbose_name='Naslov')
    content = models.OneToOneField(MathContent)
    author = models.ForeignKey(User)
    date_created = models.DateTimeField(auto_now_add=True)
    last_edit_date = models.DateTimeField(auto_now=True)
    hidden = models.BooleanField(default=False, verbose_name='Skriven')
    source = models.CharField(max_length=200, blank=True, verbose_name='Izvor')

    search_cache_elements = GenericRelation(SearchCacheElement)
    posts = PostGenericRelation(placeholder="Komentar")
    tags = TaggableManager(blank=True)
    quality_rating = RatingField(**QUALITY_RATING_ATTRS)
    difficulty_rating = RatingField(**DIFFICULTY_RATING_ATTRS)
    similar = models.ManyToManyField('self', through=SimilarTask,
        related_name='similar_backward', symmetrical=False)

    solved_count = models.IntegerField(default=0, db_index=True)

    solvable = models.BooleanField(default=True, verbose_name=u'Zadatak',
        help_text=icon_help_text(
            u'Rješivo ili ne, to jest mogu li se slati rješenja?'))

    SOLUTIONS_VISIBLE = 0
    SOLUTIONS_VISIBLE_IF_ACCEPTED = 10
    SOLUTIONS_NOT_VISIBLE = 20
    SOLUTION_SETTINGS_CHOICES = [(0, 'Uvijek vidljiva'),
        (10, 'Vidljiva samo korisnicima s prihvaćenim rješenjem'),
        (20, 'Vidljiva samo ovlaštenim korisnicima')]
    solution_settings = models.SmallIntegerField(default=0,
        verbose_name=u'Postavke rješenja', choices=SOLUTION_SETTINGS_CHOICES,
        help_text=icon_help_text(u'Postavi li se ograničenje, rješenja će biti '
            u'prikazana na popisu, ali im tekst neće biti vidljiv.'))

    # Comma-separator list of task IDs that are prerequisites for this task.
    # If prerequisites are set, solution_settings MUST NOT be SOLUTIONS_VISIBLE.
    # This makes logically more sense, and also extremely simplifies
    # the implementation. For example, we don't have to care anything about
    # the solution visibility, because solution_settings will check it anyway.
    # It is assumed that if the user already solved correctly the task itself,
    # it automatically met all prerequisites. If the author wants to add
    # new prerequisites at some point, that's his problem, it will have no
    # effect on the users that already solved the task.
    # Thus, just make sure not to show the task content in task view, list etc.
    prerequisites = models.CharField(max_length=100, verbose_name='Preduvjeti',
        blank=True, default='', help_text=icon_help_text(
            u'Popis ID-eva zadataka, odvojenih zarezom, '
            u'koji su preduvjet ovom zadatku. Korisnik će moći pristupiti '
            u'zadatku samo uz poslana i točna rješenja navedenih zadataka.'))

    ###############################
    # Derived classes
    ###############################
    # If nonempty, this Task represents actually a file.
    file_attachment = models.ForeignKey(Attachment, blank=True, null=True)
    cache_file_attachment_url = models.CharField(max_length=150, blank=True,
            default='')
    cache_file_attachment_thumbnail_url = models.CharField(max_length=150,
            blank=True, default='')

    # For lectures
    is_lecture = models.BooleanField(default=False, db_index=True)
    lecture_folder = models.ForeignKey('folder.Folder', blank=True, null=True)
    lecture_video_url = models.URLField(blank=True, max_length=200,
            verbose_name=_("Lecture video URL"))

    class Meta:
        permissions = (("can_bulk_add", "Can bulk add"), )


    def __unicode__(self):
        return u'#%d %s' % (self.id, self.name)

    def get_absolute_url(self):
        return '/task/%d/' % self.id

    def is_allowed_to_edit(self, user, perm=None):
        """
        Check if the user is allowed to solve current problem.

        Saves the result to the object for internal usage.

        If 'perm' not given, it will be retrieved automatically.
        """
        if perm is None:
            if hasattr(self, '_cache_perm'):
                perm = self._cache_perm
            else:
                perm = self.get_user_permissions(user)
        self._cache_perm = perm
        return EDIT in perm

    def is_allowed_to_solve(self, user):
        """
        Check if the user is allowed to solve current problem.

        User is allowed to solve the task if it is solvable, visible and all
        the prerequisites are met.
        """
        if not self.solvable:
            return False

        perm = self.get_user_permissions(user)
        if VIEW not in perm:
            return False

        from skoljka.task.utils import check_prerequisites_for_task
        return check_prerequisites_for_task(self, user, perm)

    def get_link(self, tooltip=False, url_suffix=''):
        # TODO: EDIT permission should immediately imply view permission
        # everywhere, not only here.

        # If prerequisites not met, do not output link.
        if EDIT not in getattr(self, '_cache_perm', []) \
                and not getattr(self, 'cache_prerequisites_met', False):
            # Do not show if this is a file or not, it doesn't matter.
            # Especially, don't put the link to the file itself!
            return mark_safe(u'<i class="icon-lock" title="Niste riješili neke '
                u'od preduvjeta za ovaj zadatak!"></i> '
                u'<span class="task-locked">{}</span>'.format(
                    xss.escape(self.name)))

        if self.file_attachment_id:
            url = self.cache_file_attachment_url
            icon = 'icon-book' if self.is_lecture else 'icon-file'
            file = u'<a href="{}" title="{}">'      \
                    u'<i class="{}"></i>'    \
                    u'</a> '.format(url, url[url.rfind('/') + 1:], icon)
        else:
            file = u''

        # If not solvable, automatically there is no tooltip.
        return mark_safe(u'{}<a href="/task/{}/{}" class="task{}">{}</a>'.format(
            file, self.id, url_suffix,
            ' task-tt-marker' if tooltip and self.solvable else '',
            xss.escape(self.name)))

    def _get_prerequisites(self):
        try:
            return [int(x) for x in self.prerequisites.split(',')]
        except ValueError:
            return []

    def is_file(self):
        return self.file_attachment_id

    def get_tr_class(self):
        """
            Return tr class for task table.
        """
        solution = getattr(self, 'cache_solution', None)
        if solution:
            cls = solution.get_html_info()['tr_class']
        elif self.hidden:
            cls = 'task-hidden'
        else:
            cls = ''

        return cls if self.solvable else cls + ' task-unsolvable'
