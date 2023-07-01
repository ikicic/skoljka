from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext

from skoljka.folder.decorators import folder_view  # Model-specific.
from skoljka.permissions.constants import EDIT_PERMISSIONS, PERMISSIONS, VIEW
from skoljka.permissions.models import (
    ObjectPermission,
    convert_permission_names_to_values,
    has_group_perm,
)
from skoljka.permissions.signals import objectpermissions_changed
from skoljka.usergroup.forms import GroupEntryForm
from skoljka.utils.decorators import response


@login_required
@response('permissions_edit.html')
def edit(request, id, type_id):
    """Check if there are any special requirements for given content type.

    Currently, only `Folders` use a special kind of permission check
    (and data preparation).
    """
    content_type = get_object_or_404(ContentType, id=type_id)

    # Model specific tuning:
    if content_type.app_label == 'folder' and content_type.model == 'folder':
        return _folder_edit(request, id, type_id, content_type)

    try:
        object = content_type.get_object_for_this_type(id=id)
    except:
        raise Http404

    # Check if the user has the permission to *edit permissions* (not just
    # to view it). Note that the object has to be PermissionsModel.
    if not object.user_has_perm(request.user, EDIT_PERMISSIONS):
        return 403
    return _edit(request, {}, id, object, type_id, content_type)


@folder_view(permission=EDIT_PERMISSIONS)
def _folder_edit(request, folder, data, *args, **kwargs):
    """Wrapper for folders."""
    # Ok, user can really edit permissions. Continue with generated data.
    return _edit(request, data, folder.id, folder, *args, **kwargs)


def _edit(request, data, id, object, type_id, content_type):
    """Actual edit view."""

    model = object.__class__

    # Convert list of strings (permission names) to the list of permission types.
    object_permissions = getattr(model, 'object_permissions', ['default'])

    permission_types = convert_permission_names_to_values(object_permissions)

    # Get the (name, value) pairs in the specific order.
    applicable_permissions = [
        (name, value) for name, value in PERMISSIONS if value in permission_types
    ]

    selected_types = [VIEW]
    form = None
    message = u''
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'remove-permissions':
            group_id = request.POST.get('group-id')
            if group_id:
                try:
                    group = Group.objects.get(id=group_id)
                except Group.DoesNotExist:
                    return 403

                to_delete = ObjectPermission.objects.filter(
                    object_id=id, content_type_id=type_id, group_id=group_id
                )
                if (
                    content_type.app_label == 'auth'
                    and content_type.model == 'group'
                    and id == group_id
                ):
                    # Don't delete group's permission to view itself.
                    to_delete = to_delete.exclude(permission_type=VIEW)
                to_delete.delete()

                objectpermissions_changed.send(
                    sender=model, instance=object, content_type=content_type
                )
        else:
            form = GroupEntryForm(request.POST, user=request.user)
            if form.is_valid():
                groups = form.cleaned_data['list']
                selected_types = [
                    x[1]
                    for x in applicable_permissions
                    if ('perm-%d' % x[1]) in request.POST
                ]

                # delete all old selected permission for given groups
                # (make sure there will be no duplicates...)
                ObjectPermission.objects.filter(
                    content_type_id=type_id,
                    object_id=id,
                    permission_type__in=selected_types,
                    group__in=groups,
                ).delete()

                # add them back
                perm = []
                for x in selected_types:
                    for y in groups:
                        perm.append(
                            ObjectPermission(
                                content_object=object, permission_type=x, group=y
                            )
                        )

                ObjectPermission.objects.bulk_create(perm)

                objectpermissions_changed.send(
                    sender=model, instance=object, content_type=content_type
                )

                message = _("Changes saved.")

                form = None  # Reset.

    if form is None:
        form = GroupEntryForm(user=request.user)

    perms = ObjectPermission.objects.filter(object_id=id, content_type=content_type)
    groups = {}
    for perm in perms:
        group = perm.group
        if group.id in groups:
            groups[group.id]._cache_permissions.append(perm.permission_type)
        else:
            groups[group.id] = group
            groups[group.id]._cache_permissions = [perm.permission_type]

    data.update(
        {
            'object': object,
            'form': form,
            'message': message,
            'groups': groups.itervalues(),
            'applicable_permissions': applicable_permissions,
            'selected_types': selected_types,
        }
    )

    return data
