﻿from django import forms
from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist

from permissions.constants import VIEW
from permissions.utils import filter_objects_with_permission

class UserEntryField(forms.CharField):
    widget = forms.Textarea(attrs={'rows':3})

    def clean(self, value):
        usernames = [x.strip() for x in value.split(',')]
        # this must be case-insensitive!
        found = User.objects.filter(username__in=usernames)

        not_found = set(usernames) - set(x.username for x in found)
        if not_found:
            raise forms.ValidationError(u'Nepostojeći korisnici: %s' \
                % ', '.join(not_found))

        return found

class GroupEntryField(forms.CharField):
    """
        Don't forget to set .user attribute!
    """
    widget = forms.Textarea(attrs={'rows':3})

    def __init__(self, *args, **kwargs):
        super(GroupEntryField, self).__init__(*args, **kwargs)
        self.user = None    # Currently logged in user, for hidden groups...

    def clean(self, value):
        if not value or not value.strip():
            return []
        names = [x.strip() for x in value.split(',')]
        # this must be case-insensitive!
        groups = Group.objects.filter(name__in=names).select_related('data')
        groups_lowercase = set(x.name.lower() for x in groups)

        error = set(x.lower() for x in names) - groups_lowercase

        # Do not immediately reject if len(error) > 0. List *all* invalid
        # inaccessible groups.

        # Check permissions. First, skip user private groups.
        usernames = User.objects.filter(username__in=groups_lowercase) \
            .values_list('username', flat=True)
        usernames = set(x.lower() for x in usernames)
        real_groups = [x for x in groups if x.name not in usernames]

        visible = filter_objects_with_permission(real_groups, self.user,
            VIEW, model=Group)

        if len(visible) != len(real_groups):
            error |= set(x.name.lower() for x in real_groups)   \
                - set(x.name.lower() for x in visible)

        if error:
            raise forms.ValidationError(
                u'Nepostojeće ili nedostupne grupe ili korisnici: %s' \
                    % ', '.join(error))

        return groups
