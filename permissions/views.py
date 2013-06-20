from django import forms
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from usergroup.forms import GroupEntryForm
from skoljka.utils.decorators import response

from permissions.constants import VIEW, EDIT_PERMISSIONS, constants
from permissions.models import ObjectPermission, has_group_perm,        \
    convert_permission_names_to_values
from permissions.signals import objectpermissions_changed

# Model specific:
from folder.utils import prepare_folder_menu


# TODO: permission to change permissions?

@login_required
@response('permissions_edit.html')
def edit(request, type_id, id):
    content_type = get_object_or_404(ContentType, id=type_id)
    try:
        object = content_type.get_object_for_this_type(id=id)
    except:
        raise Http404

    model = object.__class__

    # Model specific tuning:
    folder_tree = ''
    if content_type.app_label == 'folder' and content_type.model == 'folder':
        data = prepare_folder_menu([object], request.user)

        # When checking permissions for folders, one must chain whole path
        # to the root. That's what prepare_folder_menu anyway does.
        # FIXME: is this necessarry? this check should be done only for VIEW.
        if object.author_id != request.user.id and  \
                (not data or not data.get('folder_tree', None)):
            return 403  # Sorry, no access
        folder_tree = data['folder_tree']

    # Check if the user has the permission to *edit permissions* (not just
    # view it). Note that object has to be PermissionsModel.
    if not object.user_has_perm(request.user, EDIT_PERMISSIONS):
        return 403


    # Convert list of strings (permission names) to list of permission types
    object_permissions = getattr(model, 'object_permissions', ['default'])

    permission_types = convert_permission_names_to_values(object_permissions)

    # Get (name, value) pairs in the specific order.
    applicable_permissions = [(name, value)
        for name, value in constants if value in permission_types]


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

                ObjectPermission.objects.filter(object_id=id,
                    content_type_id=type_id, group_id=group_id).delete()
                objectpermissions_changed.send(sender=model, instance=object,
                    content_type=content_type)
        else:
            form = GroupEntryForm(request.POST)
            if form.is_valid():
                groups = form.cleaned_data['list']
                selected_types = [x[1] for x in applicable_permissions
                    if ('perm-%d' % x[1]) in request.POST]

                # delete all old selected permission for given groups
                # (make sure there will be no duplicates...)
                ObjectPermission.objects.filter(
                    content_type_id=type_id, object_id=id,
                    permission_type__in=selected_types, group__in=groups).delete()

                # add them back
                perm = []
                for x in selected_types:
                    for y in groups:
                        perm.append(ObjectPermission(content_object=object,
                            permission_type=x, group=y))

                ObjectPermission.objects.bulk_create(perm)

                objectpermissions_changed.send(sender=model, instance=object,
                    content_type=content_type)

                message = u'Promjene spremljene.'

                form = None # reset


    if form is None:
        form = GroupEntryForm()

    perms = ObjectPermission.objects.filter(object_id=id, content_type=content_type)
    groups = dict()
    for perm in perms:
        group = perm.group
        if group.id in groups:
            groups[group.id]._cache_permissions.append(perm.permission_type)
        else:
            groups[group.id] = group
            groups[group.id]._cache_permissions = [perm.permission_type]


    return {
        'object': object,
        'form': form,
        'message': message,
        'groups': groups.itervalues(),
        'applicable_permissions': applicable_permissions,
        'selected_types': selected_types,
        'folder_tree': folder_tree
    }
