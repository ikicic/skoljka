from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from usergroup.forms import GroupEntryForm
from skoljka.utils.decorators import response

from permissions.constants import VIEW, EDIT_PERMISSIONS
from permissions.constants import constants, constants_names
from permissions.models import ObjectPermission, has_group_perm


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

    # Check if the user has to permission to edit permissions.
    # Note that object has to be PermissionsModel.
    if not object.user_has_perm(request.user, EDIT_PERMISSIONS):
        return 403

    # Convert list of strings (permission names) to list of permission types
    object_permissions = getattr(model, 'Meta.object_permissions', ['default'])
    print object_permissions
    print sum([constants_names[name] for name in object_permissions], [])
    permission_types = list(set(sum(
        [constants_names[name] for name in object_permissions], [])))

    # Get (name, value) pairs and order in the specific order.
    applicable_permissions = [(name, value)
        for name, value in constants if value in permission_types]

    message = u''
    if request.method == 'POST':
        form = GroupEntryForm(request.POST)
        if form.is_valid():
            groups = form.cleaned_data['list']
            ObjectPermission.objects.filter(
                content_type=type_id, object_id=id, permission_type=VIEW).delete()

            for x in groups:
                perm = ObjectPermission(content_object=object, group=x, permission_type=VIEW)
                try:
                    perm.save()
                except IntegrityError:
                    pass

            message = u'Promjene spremljene.'
    else:
        initial = ', '.join(
            ObjectPermission.objects.filter(
                content_type=type_id, object_id=id, permission_type=VIEW
            ).values_list('group__name', flat=True)
        )
        form = GroupEntryForm(initial={'list': initial})


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
    }
