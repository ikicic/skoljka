from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.shortcuts import get_object_or_404

from skoljka.activity import action as _action
from skoljka.mathcontent.forms import MathContentForm
from skoljka.permissions.constants import EDIT, VIEW
from skoljka.permissions.models import ObjectPermission
from skoljka.usergroup.decorators import group_view
from skoljka.usergroup.forms import GroupForm, UserEntryForm, UserGroupForm
from skoljka.usergroup.models import GroupExtended, is_group_member
from skoljka.userprofile.models import user_refresh_group_cache
from skoljka.utils.decorators import response


@login_required
@group_view()
@response('usergroup_leave.html')
def leave(request, group, context_dict):
    if group.data is None:
        return (403, "Can't leave your private user-group.")

    if not context_dict['is_member']:
        return (403, "You are not a member of this group.")

    if request.method == 'POST':
        if request.POST.get('confirm') == u'1':
            request.user.groups.remove(group)

            user_refresh_group_cache([request.user.id])
            group.data.cache_member_count = group.data.get_members().count()
            group.data.save(force_update=True)
            _action.add(
                request.user,
                _action.GROUP_LEAVE,
                action_object=request.user,
                target=group,
                group=group,
            )
            return ('/usergroup/',)

    return context_dict


# TODO: optimizirati ako je moguce
@login_required
@group_view()
@response('usergroup_detail.html')
def detail(request, group, context_dict):
    if group.data is None:
        return ('/profile/%d/' % group.user_set.all()[0].id,)

    return context_dict


# TODO: perm!!
@login_required
@response()
def new(request, group_id=None):
    if group_id:
        group = get_object_or_404(
            Group.objects.select_related('data', 'data__description'), id=group_id
        )
        if not group.data:
            return (
                400,
                "You can't edit your own private user-group (or there is some data error).",
            )

        usergroup = group.data

        # https://code.djangoproject.com/ticket/7190
        # (fixed in later versions of Django...)
        usergroup.hidden = bool(usergroup.hidden)

        perm = group.get_user_permissions(request.user)
        is_member = is_group_member(group.id, request.user.id)
        if EDIT not in perm:
            return (403, "You do not have permission to edit this group's details.")

        description = usergroup.description
        edit = True
    else:
        group = usergroup = description = None
        is_member = False
        edit = False

    POST = request.POST if request.method == 'POST' else None

    group_form = GroupForm(POST, instance=group, prefix='x')
    usergroup_form = UserGroupForm(POST, instance=usergroup, prefix='y')
    description_form = MathContentForm(POST, instance=description, prefix='z')

    if request.method == 'POST':
        if (
            group_form.is_valid()
            and usergroup_form.is_valid()
            and description_form.is_valid()
        ):
            group = group_form.save()
            description = description_form.save()

            usergroup = usergroup_form.save(commit=False)
            usergroup.description = description

            if not edit:
                usergroup.group = group
                usergroup.author = request.user

                # Permissions assigned to the whole group (each member).
                # Every group member has perm to view the group itself.
                ObjectPermission.objects.create(
                    content_object=group, group=group, permission_type=VIEW
                )

            usergroup.save()

            return ('/usergroup/%d/' % group.id,)
        elif group_id:  # Reset necessary instances.
            group = get_object_or_404(
                Group.objects.select_related('data', 'data__description'), id=group_id
            )

    return (
        'usergroup_new.html',
        {
            'can_edit': True,
            'group': group,
            'edit': edit,
            'is_member': is_member,
            'new_group': not edit,
            'forms': [group_form, usergroup_form, description_form],
        },
    )


@login_required
@response('usergroup_list.html')
def list_view(request):
    groups = GroupExtended.objects.for_user(request.user, VIEW).select_related('data')

    user_group_ids = request.user.groups.values_list('id', flat=True)

    return {
        'groups': groups,
        'user_group_ids': list(user_group_ids),
    }


@login_required
@group_view()
@response('usergroup_members.html')
def members(request, group, context_dict):
    if context_dict['can_add_members'] and request.method == 'POST':
        form = UserEntryForm(request.POST)
        if form.is_valid():
            created_user_ids = []
            users = form.cleaned_data['list']
            for user in users:
                # user.groups.add(group)
                dummy, created = User.groups.through.objects.get_or_create(
                    user=user, group=group
                )
                if created:
                    created_user_ids.append(user.id)
                    _action.add(
                        request.user,
                        _action.GROUP_ADD,
                        action_object=user,
                        target=group,
                        group=group,
                    )
            # TODO: manually create function like 'group_members_update'
            user_refresh_group_cache(created_user_ids)
            group.data.cache_member_count = group.data.get_members().count()
            group.data.save()
            form = UserEntryForm()
    else:
        form = UserEntryForm()

    context_dict['form'] = form
    return context_dict
