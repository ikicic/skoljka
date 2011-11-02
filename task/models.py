from django.contrib.auth.models import User
from django.db import models
from mathcontent.models import MathContent
from taggit.managers import TaggableManager

class Task(models.Model):
    name = models.CharField(max_length=200)
    content = models.OneToOneField(MathContent)
    author = models.ForeignKey(User)
    tags = TaggableManager()

    def __unicode__(self):
        return self.name
    
    def tag_list(self):
        return " | ".join( [ "<a href=\"/search/%s/\">%s</a>" % (tag.name, tag.name) for tag in self.tags.order_by('name') ] )
