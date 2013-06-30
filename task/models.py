from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.generic import GenericRelation
from django.utils.safestring import mark_safe

from mathcontent.models import MathContent, Attachment
from permissions.models import BasePermissionsModel
from post.generic import PostGenericRelation
from rating.fields import RatingField
from search.models import SearchCacheElement
from tags.managers import TaggableManager
from skoljka.utils.models import icon_help_text

import random

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
    'on_update': 'userprofile.models.task_difficulty_on_update',
}


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
    posts = PostGenericRelation()
    tags = TaggableManager(blank=True)
    quality_rating = RatingField(**QUALITY_RATING_ATTRS)
    difficulty_rating = RatingField(**DIFFICULTY_RATING_ATTRS)
    similar = models.ManyToManyField('self', through=SimilarTask,
        related_name='similar_backward', symmetrical=False)

    solved_count = models.IntegerField(default=0, db_index=True)

    # If nonempty, this Task is a file actually.
    file_attachment = models.ForeignKey(Attachment, blank=True, null=True)
    cache_file_attachment_url = models.CharField(max_length=150, blank=True,
        default='')

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

    def __unicode__(self):
        return '#%d %s' % (self.id, self.name)

    def get_absolute_url(self):
        return '/task/%d/' % self.id

    def get_link(self, tooltip=False, url_suffix=''):
        # If prerequisites not met, do not output link.
        if not getattr(self, 'cache_prerequisites_met', False):
            # Do not show if this is a file or not, it doesn't matter.
            # Especially, don't put the link to the file itself!
            return mark_safe(u'<i class="icon-lock" title="Niste riješili neke '
                u'od preduvjeta za ovaj zadatak!"></i> '
                u'<span class="task-locked">{}</span>'.format(self.name))

        if self.file_attachment_id:
            url = self.cache_file_attachment_url
            file = u'<a href="{}" title="{}">'      \
                    u'<i class="icon-file"></i>'    \
                    u'</a> '.format(url, url[url.rfind('/') + 1:])
        else:
            file = u''

        # If not solvable, automatically there is no tooltip.
        return mark_safe(u'{}<a href="/task/{}/{}" class="task{}">{}</a>'.format(
            file, self.id, url_suffix,
            ' task-tt-marker' if tooltip and self.solvable else '',
            self.name))

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

    # deprecated?
    # TODO: preurediti, ovo je samo tmp
    # random try function
    def update_similar_tasks(self, cnt):
        from task.utils import task_similarity

        similar = SimilarTask.objects.filter(task=self).values_list('similar_id', flat=True)

        # TODO: maknuti ORDER BY RAND()
        sim = Task.objects.filter(hidden=False).exclude(id__in=similar).exclude(id=self.id).order_by('?')[:cnt]
        for x in sim:
            similarity = task_similarity(self, x)
            print 'SPAJAM ', self.id, ' SA ', x.id, ' UZ SCORE ', similarity
            SimilarTask.objects.create(task=self, similar=x, score=similarity)

        similar = SimilarTask.objects.filter(task=self).values_list('id', 'score')
        over = len(similar) - MAX_SIMILAR_TASKS
        print 'SLICNI ZADACI: ', similar
        if over > 0:
            similar = [(id, 1 / (0.001 + score)) for id, score in similar]
            total = sum(score for id, score in similar)
            print 'SLICNI ZADACI: ', similar, total
            to_delete = []
            for x in range(over):
                while True:
                    R = random.random() * total
                    for id, score in similar:
                        if R <= score:
                            break
                        else:
                            R -= score

                    if id not in to_delete:
                        break

                to_delete.append(id)

            SimilarTask.objects.filter(id__in=to_delete).delete()

            print 'IZBACUJEM', to_delete
