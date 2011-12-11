from django.db import models
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe

from mathcontent.models import MathContent
from post.generic import PostGenericRelation
from taggit.managers import TaggableManager


class Task(models.Model):
    name = models.CharField(max_length=200)
    content = models.OneToOneField(MathContent)
    author = models.ForeignKey(User)
    date_created = models.DateTimeField(auto_now_add=True)
    posts = PostGenericRelation()
    tags = TaggableManager(blank=True)

    solved_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['id']
    
    def __unicode__(self):
        return self.name
    
    def tag_list(self):
        if not hasattr(self, '_cache_tag_set'):
            self._cache_tag_set = [tag.name for tag in self.tags.order_by('name')]
        return mark_safe(u' | '.join( [ u'<a href="/search/%s/">%s</a>' % (tag, tag) for tag in self._cache_tag_set ] ))
