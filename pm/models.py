from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

from mathcontent.forms import MathContent

# TODO: moze li se messaging implementirati preko user/group permission sistema?

# deprecated
# TODO: implementirati ovo pametnije (vidi permissions)
class MessageManager(models.Manager):
    # FIXME: vraca duplikate, a .distinct() ne pomaze (vjerojatno bi se popravilo pametnijom implementacijom)
    def inbox(self, object):
        content_type = ContentType.objects.get_for_model(object)
        result = self.filter(object_id=object.id, content_type=content_type)
        if isinstance(object, User):
            group_content_type = ContentType.objects.get(app_label='auth', model='group')
            result |= self.filter(content_type=group_content_type, object_id__in=object.groups.all())
        return result;
        
class MessageContent(models.Model):
    subject = models.CharField(max_length=120)
    content = models.OneToOneField(MathContent)
    author = models.ForeignKey(User)
    date_created = models.DateTimeField(auto_now_add=True)
    
    def __unicode__(self):
        return u'#%d "%s"' % (self.id, self.subject)

class MessageRecipient(models.Model):
    group = models.ForeignKey(Group)
#    object_id = models.PositiveIntegerField()
#    content_type = models.ForeignKey(ContentType)
#    content_object = generic.GenericForeignKey()
    
    message = models.ForeignKey(MessageContent, related_name='recipients')
    
    objects = MessageManager()
