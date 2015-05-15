from django.contrib.auth.models import User, Group
from django.db import models
from django.db.models import Q
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

from permissions.constants import EDIT, VIEW, MODEL_DEFAULT, constants_names

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

    return ObjectPermission.objects.filter(
            object_id=instance.id,
            content_type=content_type,
            group_id__in=user.get_profile().get_group_ids(),
            permission_type = type,
        ).exists()

# don't waste time making values unique
def get_permissions_for_object_by_id(user, object_id, content_type_id):
    if not user.is_authenticated():
        return []
    return list(ObjectPermission.objects.filter(
            object_id=object_id,
            content_type_id=content_type_id,
            group_id__in=user.get_profile().get_group_ids(),
        ).values_list('permission_type', flat=True))

def get_permissions_for_object(user, obj):
    content_type = ContentType.objects.get_for_model(obj)
    return get_permissions_for_object_by_id(user, obj.id, content_type.id)

def convert_permission_names_to_values(names):
    permission_types = []
    for x in names:
        if isinstance(x, basestring):
            permission_types.extend(constants_names[x])
        else:
            permission_types.append(x)

    # remove duplicates
    return list(set(permission_types))


class PermissionManager(models.Manager):
    def for_user(self, user, permission_type):
        if user is not None and user.is_authenticated():
            q = Q(permissions__group_id__in=user.get_profile().get_group_ids(),
                permissions__permission_type=permission_type)

            try:
                self.model._meta.get_field_by_name('author')
                q |= Q(author_id=user.id)
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
# If necessary, put skoljka.libs.models.ModelEx here
class BasePermissionsModel(models.Model):
    """
        Extension of Model with object-level permission API.

        Note that 'objects' Manager is also replaced!

        It is assumed that the author of the model (if defined) has immediately
        all permissions. Also, if hidden is defined, non-hidden instances
        are always visible (everyone has VIEW permission granted). Otherwise,
        if hidden is not defined, no VIEW permission is given in advance.

        Use object_permissions list to specify which permissions are applicable
        to the model. You can use numbers or permission names (for more info,
        look at constants_names)
    """
    class Meta:
        abstract = True

    # Possible permissions applicable to the Model
    object_permissions = MODEL_DEFAULT

    permissions = generic.GenericRelation(ObjectPermission)
    objects = PermissionManager()

    def user_has_perm(self, user, type):
        """
            Check if given user has permission 'type'.
        """
        if user.id == getattr(self, 'author_id', -1):
            return True

        if type == VIEW and not getattr(self, 'hidden', True):
            return True

        return has_group_perm(user, self, type)

    def get_user_permissions(self, user):
        if user.id == getattr(self, 'author_id', -1):
            # TODO: cache result?
            return convert_permission_names_to_values(self.__class__.object_permissions)

        permissions = get_permissions_for_object(user, self)
        if not getattr(self, 'hidden', True):
            permissions.append(VIEW)
            if user.is_staff:
                permissions.append(EDIT)
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
