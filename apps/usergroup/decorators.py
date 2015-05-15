from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404

from permissions.constants import VIEW, EDIT, EDIT_PERMISSIONS, ADD_MEMBERS

from usergroup.models import UserGroup, is_group_member

from functools import wraps

def group_view(permission=VIEW):
    """
    Decorator for group views. Checks user permissions and prepares
    necessary context data.

    Expected function parameters:
        request, group_id, (...)
    Decorated function parameters:
        request, group, context_dict, (...)

    Decorator arguments:
        permission - permission to check

    Context dictionary:
        group - the group itself, with preloaded .data (UserGroup)
        group_content_type - UserGroup content type
        can_add_members - boolean, True if the user has ADD_MEMBERS permission
        can_edit - boolean, True if the user has EDIT permission
        can_view_permissions - boolean, True if the user has EDIT_PERMISSIONS
                permission
        is_member - boolean, True if the user is a member of the group
    """

    def decorator(func):
        def inner(request, group_id=None, *args, **kwargs):
            group = get_object_or_404(
                    Group.objects.select_related('data'), id=group_id)

            perm = group.get_user_permissions(request.user)
            if VIEW not in perm:
                return HttpResponseForbidden("You are not a member of this "
                        "group, and you cannot view it's details.")
            if permission not in perm:
                return HttpResponseForbidden("Not allowed for this action.")

            context_dict = {}
            context_dict['group'] = group
            context_dict['group_content_type'] = \
                    ContentType.objects.get_for_model(Group)
            context_dict['can_edit'] = EDIT in perm
            context_dict['can_add_members'] = ADD_MEMBERS in perm
            context_dict['can_edit_permissions'] = EDIT_PERMISSIONS in perm

            # Author of the group might not be a member.
            context_dict['is_member'] = \
                    is_group_member(group_id, request.user.id)

            return func(request, group, context_dict, *args, **kwargs)

        return wraps(func)(inner)
    return decorator
