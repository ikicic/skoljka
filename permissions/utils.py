from django.contrib.contenttypes.models import ContentType

from permissions.models import ObjectPermission

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
            group__user=user, permission_type=permission_type)  \
            .values_list('object_id', flat=True).distinct()
    else:
        return ObjectPermission.objects.filter(content_type_id=content_type_id,
            group__user=user, permission_type=permission_type,
                object_id__in=filter_ids)   \
            .values_list('object_id', flat=True).distinct()
