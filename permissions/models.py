from django.contrib.auth.models import User, Group
from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

class ObjectPermission(models.Model):
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey()
    group = models.ForeignKey(Group)

    permission_type = models.IntegerField()
    
    def __unicode__(self):
        return u'Permission %d for group %d for object %d::%d' % (self.permission_type, self.group_id, self.content_type_id, self.object_id)

    class Meta:
        unique_together = (('object_id', 'content_type', 'group', 'permission_type'),)
