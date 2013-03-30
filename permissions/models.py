from django.contrib.auth.models import User, Group
from django.db import models
from django.db.models import Q
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

from permissions.constants import VIEW, MODEL_DEFAULT

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



# TODO: rename to has_perm ?
# This cannot be in utils, because it has to import ObjectPermission...
def has_group_perm(user, instance, type, content_type=None):
    if not user.is_authenticated():
        return False

    content_type = content_type or ContentType.objects.get_for_model(instance)

    # OPTIMIZE: radi join previse
    return ObjectPermission.objects.filter(
            object_id = instance.id,
            content_type = content_type,
            group__user = user,
            permission_type = type,
        ).exists()

# don't waste time making values unique
def get_permissions_for_object_by_id(user, object_id, content_type):
    if not user.is_authenticated():
        return []
    return list(ObjectPermission.objects.filter(
            object_id=object_id, content_type=content_type, group__user=user
        ).values_list('permission_type', flat=True))

def get_permissions_for_object(user, obj):
    content_type = ContentType.objects.get_for_model(obj)
    return get_permissions_for_object_by_id(user, obj.id, content_type)



class PermissionManager(models.Manager):
    def for_user(self, user, permission_type):
        if user is not None and user.is_authenticated():
            q = Q(permissions__group__user=user,
                permissions__permission_type=permission_type)

            try:
                self.model._meta.get_field_by_name('author')
                q |= Q(author=user)
            except models.FieldDoesNotExist:
                pass

            if permission_type == VIEW:
                try:
                    self.model._meta.get_field_by_name('hidden')
                    q |= Q(hidden=False)
                except models.FieldDoesNotExist:
                    pass

            return self.filter(q)
        elif permission_type == VIEW:
            return self.filter(hidden=False)
        else:
            return self.none()


# TODO: some better name please!
class BasePermissionsModel(models.Model):
    """
        Extension of Model with object-level permission API.

        Note that 'objects' Manager is also replaced!

        It is assumed that the author of the model (if defined) has immediately
        all permissions. Also, if hidden is defined, non-hidden instances
        are always visible (everyone has VIEW permission granted).

        Use object_permissions list to specify which permissions are applicable
        to the model.
    """
    class Meta:
        abstract = True

    # Possible permissions applicable to the Model
    object_permissions = MODEL_DEFAULT

    permissions = generic.GenericRelation(ObjectPermission)
    objects = PermissionManager()

    def user_has_perm(self, user, type):
        """
            Check if given user has
        """
        if user == getattr(self, 'author', None):
            return True

        if getattr(self, 'hidden', None) is True:
            return type == VIEW

        return has_group_perm(user, self, type)

    def get_user_permissions(self, user):
        if user == getattr(self, 'author', None):
            return self.__class__.object_permissions

        permissions = get_permissions_for_object(user, self)
        if not self.hidden:
            permissions.append(VIEW)
        return permissions


# TODO: some better name please!
class PermissionsModel(BasePermissionsModel):
    """
        Adds author and hidden field by default.
    """
    hidden = models.BooleanField(default=False)
    author = models.ForeignKey(User)

    class Meta:
        abstract = True
