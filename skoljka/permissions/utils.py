from collections import defaultdict

from django.contrib.contenttypes.models import ContentType

from skoljka.permissions.constants import VIEW
from skoljka.permissions.models import ObjectPermission


def get_objects_with_permissions(descriptors, user, permission_type):
    """Given a list of (content_type_id, object_id) pairs, returns the
    dictionary {pair: object}, containing only objects for which given user has
    specified permission.

    Ignores nonexisting object IDs.
    """
    # content_type_id -> list of
    ids_dict = defaultdict(list)
    for content_type_id, object_id in descriptors:
        ids_dict[content_type_id].append(object_id)

    result = {}
    for content_type_id, ids in ids_dict.iteritems():
        model = ContentType.objects.get_for_id(content_type_id).model_class()

        # Remove duplicates here
        objects = model.objects.filter(id__in=set(ids))

        # Due to mysql bug / missing feature, it is better to separately handle
        # each content type.
        # http://bugs.mysql.com/bug.php?id=31188
        objects = filter_objects_with_permission(
            objects, user, VIEW, content_type_id=content_type_id, model=model
        )

        for x in objects:
            result[(content_type_id, x.id)] = x

    return result


def filter_objects_with_permission(
    objects, user, permission_type, content_type_id=None, model=None
):
    """Returns the list of all objects for which the given user has the
    specified permission."""
    # Filter hidden objects
    if permission_type == VIEW:
        to_check = set(
            x.id
            for x in objects
            if getattr(x, 'author_id', -1) != user.id and getattr(x, 'hidden', True)
        )
    else:
        to_check = set(x.id for x in objects if getattr(x, 'author_id', -1) != user.id)

    # Check for direct permissions, if anything to check
    ok = to_check and set(
        get_object_ids_with_exclusive_permission(
            user,
            permission_type,
            content_type_id=content_type_id,
            model=model,
            filter_ids=to_check,
        )
    )

    # Filter objects with specified permission
    return [x for x in objects if x.id not in to_check or x.id in ok]


def get_object_ids_with_exclusive_permission(
    user, permission_type, content_type_id=None, model=None, filter_ids=None
):
    """Return the IDs of objects of given model/content_type whose permission
    is exclusively given to the user (or his/her groups). That is, check only
    ObjectPermission, and not the .hidden or .author_id field.

    Used for optimization purposes (skips the model table). Don't forget to
    manually check .hidden and .author_id fields!

    If filter_ids is given, only objects with these IDs will be considered.
    """
    if not user.is_authenticated():
        return []

    content_type_id = content_type_id or ContentType.objects.get_for_model(model).id

    # TODO: Optimize (remove unnecessary JOIN)
    if not filter_ids:
        return (
            ObjectPermission.objects.filter(
                content_type_id=content_type_id,
                group_id__in=user.get_profile().get_group_ids(),
                permission_type=permission_type,
            )
            .values_list('object_id', flat=True)
            .distinct()
        )
    else:
        return (
            ObjectPermission.objects.filter(
                content_type_id=content_type_id,
                group_id__in=user.get_profile().get_group_ids(),
                permission_type=permission_type,
                object_id__in=filter_ids,
            )
            .values_list('object_id', flat=True)
            .distinct()
        )
