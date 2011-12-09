from django.db import models
from django.contrib.auth.models import User

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

    def __unicode__(self):
        return self.name
    
    def tag_list(self):
        return " | ".join( [ "<a href=\"/search/%s/\">%s</a>" % (tag.name, tag.name) for tag in self.tags.order_by('name') ] )
