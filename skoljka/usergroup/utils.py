from django.contrib.auth.models import User

from skoljka.activity import action as _action
from skoljka.userprofile.models import user_refresh_group_cache


def add_users_to_group(users, group, added_by=None):
    """Add one or more users to a group.

    If `added_by` is specified and non-None, a GROUP_ADD action will be added
    for each new member."""

    created_user_ids = []
    for user in users:
        _unused, created = User.groups.through.objects.get_or_create(
            user=user, group=group
        )

        if created:
            created_user_ids.append(user.id)
            if added_by:
                _action.add(
                    added_by,
                    _action.GROUP_ADD,
                    action_object=user,
                    target=group,
                    group=group,
                )

    user_refresh_group_cache(created_user_ids)
    group.data.cache_member_count = group.data.get_members().count()
    group.data.save()
