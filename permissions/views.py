from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from permissions.constants import VIEW
from permissions.models import PerObjectGroupPermission
from usergroup.forms import GroupEntryForm

# TODO: permission to change permissions?

@login_required
def edit(request, type_id, id):
    content_type = get_object_or_404(ContentType, id=type_id)
    try:
        object = content_type.get_object_for_this_type(id=id)
    except:
        raise Http404

    message = u''
    if request.method == 'POST':
        form = GroupEntryForm(request.POST)
        if form.is_valid():
            groups = form.cleaned_data['list']
            PerObjectGroupPermission.objects.filter(
                content_type=type_id, object_id=id, permission_type=VIEW).delete()
                
            for x in groups:
                perm = PerObjectGroupPermission(content_object=object, group=x, permission_type=VIEW)
                try:
                    perm.save()
                except IntegrityError:
                    pass
                    
            message = u'Promjene spremljene.'
    else:
        initial = ', '.join(
            PerObjectGroupPermission.objects.filter(                        \
                content_type=type_id, object_id=id, permission_type=VIEW    \
            ).values_list('group__name', flat=True)
        )
        form = GroupEntryForm(initial={'list': initial})
        
    
    perms = PerObjectGroupPermission.objects.filter(object_id=id, content_type=content_type)
    groups = dict()
    for perm in perms:
        group = perm.group
        if group.id in groups:
            groups._cache_permissions.append(perm.id)
        else:
            groups[group.id] = group
            groups[group.id]._cache_permissions = [perm.id]


    return render_to_response('permissions_edit.html', {
            'object': object,
            'form': form,
            'message': message,
            'groups': groups.itervalues(),
            }, context_instance=RequestContext(request))
