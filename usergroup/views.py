from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from activity import action as _action
from mathcontent.forms import MathContentForm
from permissions.constants import VIEW, EDIT, EDIT_PERMISSIONS, ADD_MEMBERS
from permissions.models import ObjectPermission
from userprofile.models import user_refresh_group_cache

from usergroup.forms import GroupForm, UserGroupForm, UserEntryForm
from usergroup.models import UserGroup, GroupExtended

from skoljka.utils.decorators import response

@login_required
@response('usergroup_leave.html')
def leave(request, group_id=None):
    group = get_object_or_404(Group.objects.select_related('data'), id=group_id)
    if group.data is None:
        return (403, 'Can\'t leave your private user-group.')

    # TODO: ovaj query vjerojatno radi nepotreban JOIN
    is_member = request.user.groups.filter(id=group_id).exists()
    if not is_member:
        return (403, 'You are not member of this group.')

    print request.POST
    if request.method == 'POST':
        if request.POST.get('confirm') == u'1':
            request.user.groups.remove(group)
            # TODO: manually create function like 'group_members_update'
            user_refresh_group_cache([request.user.id])
            group.data.member_count = User.groups.through.objects.filter(group=group).count()
            group.data.save(force_update=True)
            _action.add(request.user, _action.GROUP_LEAVE,
                action_object=request.user, target=group, public=False,
                group=group)
            return ('/usergroup/', )

    return {'group': group}

#TODO: optimizirati ako je moguce
@login_required
@response('usergroup_detail.html')
def detail(request, group_id=None):
    group = get_object_or_404(Group.objects.select_related('data'), id=group_id)

    # FIXME: pipkavo
    if group.data is None:
        return ('/profile/%d/' % group.user_set.all()[0].id,)

    perm = group.data.get_user_permissions(request.user)
    is_member = group.data.is_member(request.user)

    if VIEW not in perm:
        return (403, 'You are not member of this group, and you cannot view it\'s details.')


    return {
        'group': group,
        'is_member': is_member,
        'can_edit': EDIT in perm,
        'can_add_members': ADD_MEMBERS in perm,
    }


# TODO: perm!!
@login_required
@response()
def new(request, group_id=None):
    if group_id:
        group = get_object_or_404(Group.objects.select_related('data', 'data__description'), id=group_id)
        if not group.data:
            return (400, 'You can\'t edit your own private user-group (or there is some data error).')

        usergroup = group.data

        # https://code.djangoproject.com/ticket/7190
        # (fixed in later versions of Django...)
        usergroup.hidden = bool(usergroup.hidden)

        perm = usergroup.get_user_permissions(request.user)
        if EDIT not in perm:
            return (403, 'You do not have permission to edit this group\'s details.')

        description = usergroup.description
        edit = True
    else:
        group = usergroup = description = None
        edit = False

    POST = request.POST if request.method == 'POST' else None

    group_form = GroupForm(POST, instance=group, prefix='x')
    usergroup_form = UserGroupForm(POST, instance=usergroup, prefix='y')
    description_form = MathContentForm(POST, instance=description, prefix='z')

    if request.method == 'POST':
        if group_form.is_valid() and usergroup_form.is_valid() and description_form.is_valid():
            group = group_form.save()
            description = description_form.save();

            usergroup = usergroup_form.save(commit=False)
            usergroup.description = description

            if not edit:
                usergroup.group = group
                usergroup.author = request.user

                # permissions assigned to whole group (each member)
                # every group member has perm to view it
                ObjectPermission.objects.create(content_object=group,
                    group=group, permission_type=VIEW)

            usergroup.save()

            return ('/usergroup/%d/' % group.id, )
        else: # reset necessary instances...
            group = get_object_or_404(Group.objects.select_related(
                'data', 'data__description'), id=group_id)

    return ('usergroup_new.html', {
        'can_edit': True,
        'group': group,
        'edit': edit,
        'new_group': not edit,
        'forms': [group_form, usergroup_form, description_form],
    })

@login_required
@response('usergroup_list.html')
def list_view(request):
    groups = GroupExtended.objects.for_user(request.user, VIEW) \
        .select_related('data')

    user_group_ids = request.user.groups.values_list('id', flat=True)

    return {
        'groups': groups,
        'user_group_ids': list(user_group_ids),
    }


@login_required
@response('usergroup_members.html')
def members(request, group_id=None):
    group = get_object_or_404(Group.objects.select_related('data'), id=group_id)
    perm = group.data.get_user_permissions(request.user)
    is_member = group.data.is_member(request.user)

    if VIEW not in perm:
        return (403, 'You do not have permission to edit this group\'s details.')

    if ADD_MEMBERS in perm and request.method == 'POST':
        form = UserEntryForm(request.POST)
        if form.is_valid():
            created_user_ids = []
            users = form.cleaned_data['list']
            for user in users:
                #user.groups.add(group)
                dummy, created = User.groups.through.objects.get_or_create(user=user, group=group)
                if created:
                    created_user_ids.append(user.id)
                    _action.add(request.user, _action.GROUP_ADD,
                        action_object=user, target=group, public=False, group=group)
            # TODO: manually create function like 'group_members_update'
            user_refresh_group_cache(created_user_ids)
            group.data.member_count = group.data.get_users().count()
            group.data.save()
            form = UserEntryForm()
    else:
        form = UserEntryForm()


    return {
        'group': group,
        'form': form,
        'is_member': is_member,
        'can_view_perm': EDIT_PERMISSIONS in perm,
        'can_edit': EDIT in perm,
        'can_add_members': ADD_MEMBERS in perm,
    }
