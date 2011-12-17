from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from permissions.constants import VIEW
#from permissions.models import PerObjectUserPermission
from permissions.models import PerObjectGroupPermission
#from usergroup.forms import SeperatedUserAndGroupEntryForm
from usergroup.forms import GroupEntryForm

def edit(request, type_id=None, id=None):
    content_type = get_object_or_404(ContentType, id=type_id)
    try:
        object = content_type.get_object_for_this_type(id=id)
    except:
        raise Http404

    message = u''
    if request.method == 'POST':
#        form = SeperatedUserAndGroupEntryForm(request.POST)
        form = GroupEntryForm(request.POST)
        if form.is_valid():
#            users, groups = form.cleaned_data['list']
#            PerObjectUserPermission.objects.filter(
#                content_type=type_id, object_id=id, permission_type=VIEW).delete()
            groups = form.cleaned_data['list']
            PerObjectGroupPermission.objects.filter(
                content_type=type_id, object_id=id, permission_type=VIEW).delete()

# TODO: osigurati da entryfield vraca unique, pa ovdje maknuti try/except
#            for x in users:
#                perm = PerObjectUserPermission(content_object=object, user=x, permission_type=VIEW)
#                try:
#                    perm.save()
#                except IntegrityError:
#                    pass
                
            for x in groups:
                perm = PerObjectGroupPermission(content_object=object, group=x, permission_type=VIEW)
                try:
                    perm.save()
                except IntegrityError:
                    pass
                    
            message = u'Promjene spremljene.'
    else:
#        initial = [x for x in PerObjectUserPermission.objects.filter(               \
#                        content_type=type_id, object_id=id, permission_type=VIEW    \
#                    ).values_list('user__username', flat=True)]                     \
        initial = [x for x in PerObjectGroupPermission.objects.filter(              \
                        content_type=type_id, object_id=id, permission_type=VIEW     \
                    ).values_list('group__name', flat=True)]
        print 'ovdje'
        print initial
        initial = ', '.join([x for x in initial])
#        form = SeperatedUserAndGroupEntryForm(initial={'list': initial})
        form = GroupEntryForm(initial={'list': initial})
        
    return render_to_response('permissions_edit.html', {
            'object': object,
            'form': form,
            'message': message,
            }, context_instance=RequestContext(request))
