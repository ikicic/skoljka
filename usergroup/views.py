from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from mathcontent.forms import MathContentForm
from usergroup.forms import GroupForm, UserEntryForm
from usergroup.models import UserGroup


#TODO: optimizirati ako je moguce
@login_required
def detail(request, group_id=None):
    group = get_object_or_404(Group.objects.select_related('data'), pk=group_id)
    if request.method == 'POST':
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
        }, context_instance=RequestContext(request))

        
@login_required
def list(request):
    if request.method == 'POST':
        group_form = GroupForm(request.POST)
        description_form = MathContentForm(request.POST)
        if group_form.is_valid() and description_form.is_valid():
            group = group_form.save()
            description = description_form.save();
            
            user_group = UserGroup(group=group, description=description, author=request.user)
            user_group.save()
            
            return HttpResponseRedirect('/usergroup/%d/' % group.pk)
    else:
        group_form = GroupForm()
        description_form = MathContentForm()
    
    return render_to_response('usergroup_list.html', {
            'forms': [group_form, description_form],
            'groups': Group.objects.all(),
        }, context_instance=RequestContext(request))
