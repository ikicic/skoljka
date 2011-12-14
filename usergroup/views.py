from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from mathcontent.forms import MathContentForm
from permissions.constants import ALL, EDIT, VIEW, ADD_MEMBERS
from permissions.models import PerObjectGroupPermission
from permissions.utils import get_permissions_for_object
from usergroup.forms import GroupForm, UserGroupForm, UserEntryForm
from usergroup.models import UserGroup, GroupExtended


#TODO: optimizirati ako je moguce
@login_required
def detail(request, group_id=None):
    group = get_object_or_404(Group.objects.select_related('data'), id=group_id)

    if group.data.author == request.user:
        perm = ALL
        is_member = True
    else:
        perm = get_permissions_for_object(request.user, group)
        is_member = request.user.groups.filter(id=group_id).exists()
        if not group.data.hidden:
            perm.append(VIEW)

    # TODO: nekakav drugi signal
    if VIEW not in perm:
        raise Http404

# TODO: odvojiti ovaj view od ostalog (?)
    if ADD_MEMBERS in perm and request.method == 'POST':
        form = UserEntryForm(request.POST)
        if form.is_valid():
            users = form.cleaned_data['list']
            for user in users:
                user.groups.add(group)
            group.data.member_count = group.data.get_users().count()
            group.data.save()
            form = UserEntryForm()
    else:
        form = UserEntryForm()
    
    return render_to_response('usergroup_detail.html', {
            'form': form,
            'group': group,
            'is_member': is_member,
            'can_add_members': ADD_MEMBERS in perm,
        }, context_instance=RequestContext(request))

        
@login_required
def list(request):

# TODO: odvojiti add view od list view-a
    if request.method == 'POST':
        group_form = GroupForm(request.POST)
        usergroup_form = UserGroupForm(request.POST)
        description_form = MathContentForm(request.POST)
        if group_form.is_valid() and usergroup_form.is_valid() and description_form.is_valid():
            group = group_form.save()
            description = description_form.save();
            usergroup = usergroup_form.save(commit=False)
            
            usergroup.group = group
            usergroup.description = description
            usergroup.author = request.user
            usergroup.save()

# DEBUG: ovo je samo debug
            for perm in [VIEW, ADD_MEMBERS]:
                self_perm = PerObjectGroupPermission(content_object=group, group=group, permission_type=perm)
                self_perm.save()
            
            return HttpResponseRedirect('/usergroup/%d/' % group.id)
    else:
        group_form = GroupForm()
        usergroup_form = UserGroupForm()
        description_form = MathContentForm()
    
    return render_to_response('usergroup_list.html', {
            'forms': [group_form, usergroup_form, description_form],
            'groups': GroupExtended.objects.for_user(request.user, VIEW).select_related('data'),
        }, context_instance=RequestContext(request))
