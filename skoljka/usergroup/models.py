from django.contrib.auth.models import Group, User
from django.contrib.contenttypes import generic
from django.db import models
from django.db.models import Q
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from skoljka.mathcontent.models import MathContent
from skoljka.permissions.constants import *
from skoljka.permissions.models import (
    BasePermissionsModel,
    ObjectPermission,
    get_permissions_for_object,
    has_group_perm,
)


def is_group_member(group_id, user_id):
    return User.groups.through.objects.filter(
        user_id=user_id, group_id=group_id
    ).exists()


# TODO: optimizirati ovaj upit, npr. rucno dati prava autoru, da se ovdje
#       ne treba to navoditi


class GroupPermissionManager(models.Manager):
    def for_user(self, user, permission_type):
        if user is not None and user.is_authenticated():
            # mora biti .distinct(), zbog svih tih silnih join-eva
            return self.filter(
                Q(data__hidden=False)
                | Q(data__author_id=user.id)
                | Q(
                    objpermissions__group_id__in=user.get_profile().get_group_ids(),
                    objpermissions__permission_type=permission_type,
                )
            ).distinct()
        else:
            return self.filter(data__hidden=False)


# FIXME: nesto ne stima vezano uz ovo, izgleda da on ne tretira kao Group
# za svaku grupu radi dodatan query (!) (mozda je to problem zbog neceg drugog)
class GroupExtended(Group):
    """
    It is not easily possible to get Group queryset with filters
    related to UserGroup.
    """

    objects = GroupPermissionManager()

    class Meta:
        proxy = True


class UserGroup(models.Model):
    group = models.OneToOneField(Group, related_name='data')
    description = models.OneToOneField(MathContent)
    author = models.ForeignKey(User)
    date_created = models.DateTimeField(auto_now_add=True)
    hidden = models.BooleanField(default=False, verbose_name=_("Hidden"))

    cache_member_count = models.IntegerField(default=0)

    def __unicode__(self):
        return self.group.name

    def get_absolute_url(self):
        return '/usergroup/%d/' % self.id

    def get_members(self):
        return User.objects.filter(groups__pk=self.group.pk)


# iako ovo izgleda jako cudno (grupna prava za grupe), zapravo je jako korisno
# grupa ima sama sebi dodijeljena neka prava (npr. VIEW)

# problem oko related_name, umjesto defaultnog 'group' stavio sam 'groups' (ikicic)
# 'permissions' would be in conflict with the existing Group.permissions!
Group.add_to_class(
    'objpermissions', generic.GenericRelation(ObjectPermission, related_name='groups')
)

# Manually extending an existing class, not such a smart idea...
group__object_permissions = MODEL_DEFAULT + [ADD_MEMBERS]


def group__user_has_perm(self, user, type):
    """
    Manual implementation of user_has_perm (BasePermissionsModel), as we can't
    extend Group class.
    """
    data = self.data
    if data:
        if user.id == data.author_id:
            return True
        if type == VIEW and not data.hidden:
            return True
    return has_group_perm(user, self, type)


def group__get_user_permissions(self, user):
    """
    Manual implementation of get_user_permissions (BasePermissionsModel), as
    we can't extend Group class.
    """
    data = self.data
    if data and data.author_id == user.id:
        return group__object_permissions
    else:
        perm = get_permissions_for_object(user, self)
        if not (data and data.hidden):
            perm.append(VIEW)
        return perm


Group.add_to_class('object_permissions', group__object_permissions)
Group.add_to_class('user_has_perm', group__user_has_perm)
Group.add_to_class('get_user_permissions', group__get_user_permissions)
