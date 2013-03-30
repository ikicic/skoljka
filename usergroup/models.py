from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes import generic
from django.utils.safestring import mark_safe

from permissions.constants import *
from permissions.models import ObjectPermission, get_permissions_for_object
from mathcontent.models import MathContent

# TODO: optimizirati ovaj upit, npr. rucno dati prava autoru, da se ovdje
#       ne treba to navoditi

class GroupPermissionManager(models.Manager):
    def for_user(self, user, permission_type):
        # ovdje postoji ovaj if, iako je svugdje login_required
        if user is not None and user.is_authenticated():
            # mora biti .distinct(), zbog svih tih silnih join-eva
            return self.filter(
                  Q(data__hidden=False)
                | Q(data__author=user)
                | Q(permissions__group__user=user, permissions__permission_type=permission_type)).distinct()
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
    hidden = models.BooleanField(default=False, verbose_name='Sakriveno')

    member_count = models.IntegerField(default=0)

    # DEPRECATED
    def __unicode__(self):
        return mark_safe(u'[<a href="/usergroup/%d/">%s</a>]' % (self.group_id, self.group.name))

    def get_absolute_url(self):
        return '/usergroup/%d/' % self.id

    def get_users(self):
        return User.objects.filter(groups__pk=self.group.pk)

    def get_user_permissions(self, user):
        """
            Note that we would rather stick permission to Group, and not to
            UserGroup. That's why we don't use PermissionsModel.
        """
        if self.author == user:
            perm = MODEL_DEFAULT + [ADD_MEMBERS]
        else:
            perm = get_permissions_for_object(user, self.group)
            if not self.hidden:
                perm.append(VIEW)
        return perm

    def is_member(self, user):
        return User.groups.through.objects.filter(user=user, group=self.group).exists()

# iako ovo izgleda jako cudno (grupna prava za grupe), zapravo je jako korisno
# grupa ima sama sebi dodijeljena neka prava (npr. VIEW)
# TODO: zasto onda postoji is_member (koja je ipak bitna informacija)?

# problem oko related_name, umjesto defaultnog 'group' stavio sam 'groups' (ikicic)
Group.add_to_class('permissions', generic.GenericRelation(ObjectPermission, related_name='groups'))
