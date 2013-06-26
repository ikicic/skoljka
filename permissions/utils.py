from django.contrib.contenttypes.models import ContentType

from permissions.constants import VIEW
from permissions.models import ObjectPermission

def filter_objects_with_permission(objects, user, permission_type,
        content_type_id=None, model=None):
    """
        Returns the list of all objects for which the given user has
        the specified permission.
    """
    # Filter hidden objects
    if permission_type == VIEW:
        to_check = set(x.id for x in objects            \
            if getattr(x, 'author_id', -1) != user.id   \
                or getattr(x, 'hidden', True))
    else:
        to_check = set(x.id for x in objects            \
            if getattr(x, 'author_id', -1) != user.id)

    # Check for direct permissions, if anything to check
    ok = to_check and set(get_object_ids_with_exclusive_permission(user,
        permission_type, content_type_id=content_type_id, model=model,
        filter_ids=to_check))

    # Filter objects with specified permission
    return [x for x in objects if x.id not in to_check or x.id in ok]

def get_object_ids_with_exclusive_permission(user, permission_type,
        content_type_id=None, model=None, filter_ids=None):
    """
        Return IDs of objects of given model/content_type, whose permission
        is exclusively given to the user (or his/her groups). I.e. check
        only ObjectPermission, and not the .hidden or .author_id field.

        For optimization purposes (skips model table). Don't forget to manually
        check .hidden and .author_id fields!

        If filter_ids is given, only objects with these IDs will be considered.
    """

    content_type_id = content_type_id   \
        or ContentType.objects.get_for_model(model).id

    # TODO: Optimize (remove unnecessary JOIN)
    if not filter_ids:
        return ObjectPermission.objects.filter(content_type_id=content_type_id,
                group_id__in=user.get_profile().get_group_ids(),
                permission_type=permission_type)  \
            .values_list('object_id', flat=True).distinct()
    else:
        return ObjectPermission.objects.filter(content_type_id=content_type_id,
                group_id__in=user.get_profile().get_group_ids(),
                permission_type=permission_type, object_id__in=filter_ids)   \
            .values_list('object_id', flat=True).distinct()
