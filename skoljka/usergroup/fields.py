from django import forms
from django.contrib.auth.models import Group, User
from django.core.exceptions import ObjectDoesNotExist

from skoljka.permissions.constants import VIEW
from skoljka.permissions.utils import filter_objects_with_permission
from skoljka.usergroup.models import UserGroup


class UserEntryField(forms.CharField):
    widget = forms.Textarea(attrs={'rows': 3})

    def clean(self, value):
        usernames = [x.strip().lower() for x in value.split(',') if x.strip()]
        # this must be case-insensitive!
        found = User.objects.filter(username__in=usernames)
        if self.required and not found:
            raise forms.ValidationError(self.error_messages['required'])

        not_found = set(usernames) - set(x.username.lower() for x in found)
        if not_found:
            raise forms.ValidationError(
                u"Nepostojeći korisnici: %s" % ", ".join(not_found)
            )

        return found


class GroupEntryField(forms.CharField):
    """
    Don't forget to set .user attribute!
    """

    widget = forms.Textarea(attrs={'rows': 3})

    def __init__(self, *args, **kwargs):
        super(GroupEntryField, self).__init__(*args, **kwargs)
        self.user = None  # Currently logged in user, for hidden groups...

    def clean(self, value):
        if not value or not value.strip():
            if self.required:
                raise forms.ValidationError(self.error_messages['required'])
            return []
        names = [x.strip().lower() for x in value.split(',')]
        # this must be case-insensitive!
        groups = Group.objects.filter(name__in=names).select_related('data')

        error = set(names) - set(x.name.lower() for x in groups)
        # Do not immediately reject if len(error) > 0. List *all* invalid or
        # inaccessible groups.

        # Check permissions. Skip user private groups.
        usergroups = [x.data for x in groups if x.data]
        visible = filter_objects_with_permission(
            usergroups, self.user, VIEW, model=UserGroup
        )

        if len(visible) != len(usergroups):
            hidden_ids = set(x.group_id for x in usergroups) - set(
                x.group_id for x in visible
            )
            error |= set(x.name.lower() for x in groups if x.id in hidden_ids)

        if error:
            raise forms.ValidationError(
                u"Nepostojeće ili nedostupne grupe ili korisnici: %s" % ", ".join(error)
            )

        return groups
