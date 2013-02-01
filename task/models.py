from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.generic import GenericRelation
from django.utils.safestring import mark_safe

from mathcontent.models import MathContent
from permissions.models import PerObjectGroupPermission
#from permissions.models import PerObjectUserPermission
from permissions.constants import VIEW
from permissions.utils import has_group_perm
from post.generic import PostGenericRelation
from rating.fields import RatingField
from search.models import SearchCacheElement
from tags.managers import TaggableManager

from task.utils import task_similarity

import random

MAX_SIMILAR_TASKS = 20

# TODO: rename "author" to "added_by" (or add another column "added_by")
# TODO: rename "name" to "title"

QUALITY_RATING_ATTRS = {
    'range': 5,
    'titles': [u'Loš. Dosadan.', u'Ima i boljih.', u'Dobar zadatak.',
        u'Jako dobar. Zanimljiv.', u'Izvrstan. Vrlo zanimljiv.'],
}

DIFFICULTY_RATING_ATTRS = {
    'range': 10,
    'titles': [u'OŠ lakši', u'OŠ teži', u'SŠ lakši', u'SŠ teži',
        u'Srednje težine', u'Shortlist 1/2', u'Shortlist 3/4', u'Shortlist 5/6',
        u'Shortlist 7/8', u'Nerješiv'],
    'on_update': 'userprofile.models.task_difficulty_on_update',
}


# ovdje ili u recommend?
class SimilarTask(models.Model):
    task = models.ForeignKey('Task', db_index=True, related_name='from')
    similar = models.ForeignKey('Task', db_index=True, related_name='to')
    score = models.FloatField(db_index=True)

class TaskPermissionManager(models.Manager):
    def for_user(self, user, permission_type):
        if user is not None and user.is_authenticated():
            # yeah, right...
            return self.filter(
                  Q(hidden=False)
                | Q(author=user)
#                | Q(user_permissions__user=user, user_permissions__permission_type=permission_type)
                | Q(group_permissions__group__user=user, group_permissions__permission_type=permission_type))
        else:
            return self.filter(hidden=False)


class Task(models.Model):
    # napomena: cache za Solution POST_SEND activity ovisi o ovom max_length, nemojte previse povecavati
    name = models.CharField(max_length=120, verbose_name='Naslov')
    content = models.OneToOneField(MathContent)
    author = models.ForeignKey(User)
    date_created = models.DateTimeField(auto_now_add=True)
    last_edit_date = models.DateTimeField(auto_now=True)
    hidden = models.BooleanField(default=False, verbose_name='Sakriven')
    source = models.CharField(max_length=200, blank=True, verbose_name='Izvor')
    
    search_cache_elements = GenericRelation(SearchCacheElement)
    group_permissions = generic.GenericRelation(PerObjectGroupPermission)
    posts = PostGenericRelation()
    tags = TaggableManager(blank=True)
    quality_rating = RatingField(**QUALITY_RATING_ATTRS)
    difficulty_rating = RatingField(**DIFFICULTY_RATING_ATTRS)
    similar = models.ManyToManyField('self', through=SimilarTask, related_name='similar_backward', symmetrical=False)

    solved_count = models.IntegerField(default=0, db_index=True)
    
    objects = TaskPermissionManager()

    class Meta:
        ordering = ['id']
    
    def __unicode__(self):
        return '#%d %s' % (self.id, self.name)
        
    def get_absolute_url(self):
        return '/task/%d/' % self.id
        
    def get_link(self):
        return mark_safe('<a href="/task/%d/" class="task">%s</a>' % (self.id, self.name))

    def has_perm(self, user, type):
        if type == VIEW and not self.hidden:
            return True
        return user.is_staff or self.author == user or has_group_perm(user, self, type)
        
    def get_tag_ids(self):
        if not hasattr(self, '_cache_tag_ids'):
            self._cache_tag_ids = self.tags.values_list('id', flat=True)
        return self._cache_tag_ids


    # deprecated?
    # TODO: preurediti, ovo je samo tmp
    # random try function
    def update_similar_tasks(self, cnt):
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
