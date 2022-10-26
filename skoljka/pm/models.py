from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

from skoljka.mathcontent.forms import MathContent

class MessageContent(models.Model):
    subject = models.CharField(max_length=120)
    content = models.OneToOneField(MathContent)
    author = models.ForeignKey(User, related_name='my_messages')
    date_created = models.DateTimeField(auto_now_add=True)
    
    recipients = models.ManyToManyField(User, related_name='messages', through='MessageRecipient')
    groups = models.ManyToManyField(Group, related_name='messages')
    
    deleted_by_author = models.BooleanField(default=False)
    
    def __unicode__(self):
        return u'#%d "%s"' % (self.id, self.subject)

class MessageRecipient(models.Model):
    recipient = models.ForeignKey(User)
    message = models.ForeignKey(MessageContent)
    
    read = models.SmallIntegerField(default=0)   # or IntegerField?
    deleted = models.BooleanField(default=0)
    
    # potrebni multi indeksi:
    # (recipient, read)
    # (recipient, deleted)
    # moze i 
    # (recipient, deleted, read)
