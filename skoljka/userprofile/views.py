from urllib import quote_plus

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.db.models import Max, Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext
from django.views.decorators.debug import sensitive_post_parameters
from registration.views import register as _register

from skoljka.permissions.constants import VIEW
from skoljka.recommend.models import UserTagScore
from skoljka.solution.models import Solution, SolutionStatus
from skoljka.solution.templatetags.solution_tags import cache_solution_info
from skoljka.task.models import DIFFICULTY_RATING_ATTRS, Task
from skoljka.task.utils import check_prerequisites_for_tasks
from skoljka.userprofile.forms import (
    UserCreationForm,
    UserEditForm,
    UserProfileEditForm,
)
from skoljka.userprofile.models import UserProfile
from skoljka.userprofile.registration_backend import Backend
from skoljka.utils.decorators import response
from skoljka.utils.templatetags.utils_tags import email_link

# Note: In registration, we handle final_url separately from the
# UserCreationForm.


def logout(request):
    """
    Logout and redirect to the home page.
    """
    auth_logout(request)
    return redirect('/')


@sensitive_post_parameters()
def new_register(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/')
    if request.method == 'POST':
        email = quote_plus(request.POST.get('email'))
        success_url = '/accounts/register/complete/?email=' + email
    else:
        success_url = None
    return _register(
        request,
        'skoljka.userprofile.registration_backend.Backend',
        form_class=UserCreationForm,
        success_url=success_url,
        extra_context={'final_url': request.POST.get('final_url', '/')},
    )


@sensitive_post_parameters()
@response('registration/registration_complete.html')
def registration_complete(request):
    if request.user.is_authenticated():
        return ('/',)
    return {
        'contact_link': email_link(settings.REGISTRATION_CONTACT_EMAIL),
        'email': request.GET.get('email', ''),
    }


@response('registration/activation_complete.html')
def activation_complete(request):
    return {'final_url': Backend().get_final_url(request)}


@login_required
@response('memberlist.html')
def member_list(request):
    """
    Show the list of all members. Hide inactive users, as well as the
    main admin.
    """
    user_list = (
        User.objects.filter(is_active=1).select_related('profile').order_by('id')
    )

    # TODO: do not hardcode the username
    user_list = [user for user in user_list if user.username != 'arhiva']

    return {'user_list': user_list}


@login_required
def edit(request):
    profile = request.user.get_profile()

    success = None
    if request.method == 'POST':
        form1 = UserEditForm(request.POST, instance=request.user)
        form2 = UserProfileEditForm(request.POST, instance=profile)
        if form1.is_valid() and form2.is_valid():
            request.user = form1.save()
            profile = form2.save()
            success = True
    else:
        form1 = UserEditForm(instance=request.user)
        form2 = UserProfileEditForm(instance=profile)

    return render_to_response(
        'profile_edit.html',
        {
            'forms': [form1, form2],
            'success': success,
        },
        context_instance=RequestContext(request),
    )


@login_required
def profile(request, pk):
    if request.user.pk == pk:
        user = request.user
        solutions = Solution.objects
        tasks = Task.objects
    else:
        user = get_object_or_404(User.objects.select_related('profile'), pk=pk)
        solutions = Solution.objects.filter_visible_tasks_for_user(request.user)
        tasks = Task.objects.for_user(request.user, VIEW)

    # DEPRECATED. Distribution should be now updated automatically...
    # user.profile.refresh_diff_distribution()

    distribution = user.profile.get_diff_distribution()
    high = max(distribution)
    if high > 0:
        scale = 100.0 / max(high, 10)
        scaled = [int(x * scale) for x in distribution]
        distribution = zip(DIFFICULTY_RATING_ATTRS['titles'], scaled, distribution)
    else:
        distribution = None

    if request.user.id == pk:
        visible_groups = user.groups.select_related('data')
    else:
        where = (
            '((SELECT id FROM auth_user_groups AG2 '
            'WHERE AG2.group_id = auth_group.id AND AG2.user_id = {} '
            'LIMIT 1)'
            ' IS NOT NULL OR usergroup_usergroup.hidden != 0)'.format(user.id)
        )
        visible_groups = user.groups.select_related('data').extra(where=[where])

    visible_groups = visible_groups.exclude(id=user.get_profile().private_group_id)

    tags = (
        UserTagScore.objects.filter(user=user)
        .select_related('tag')
        .order_by('-cache_score')[:10]
    )

    solutions = (
        solutions.filter(author_id=pk).select_related('task').order_by('-date_created')
    )
    todo = solutions.filter(status=SolutionStatus.TODO)[:10]
    solved = solutions.filter(
        status__in=[SolutionStatus.AS_SOLVED, SolutionStatus.SUBMITTED]
    )[:10]

    if pk != request.user.pk:
        # TODO: optimize, do not load unnecessary my_solution
        # (separate check_accessibility should_obfuscate?)
        cache_solution_info(request.user, solved)
        for x in solved:
            x.t_can_view, dummy = x.check_accessibility(
                request.user, x._cache_my_solution
            )

    task_added = tasks.filter(author_id=pk).order_by('-id')[:10]

    all_tasks = [x.task for x in solved] + [x.task for x in todo] + list(task_added)

    check_prerequisites_for_tasks(all_tasks, request.user)

    return render_to_response(
        'profile_detail.html',
        {
            'profile': user,
            'distribution': distribution,
            'visible_groups': visible_groups,
            'tags': tags,
            'todo': todo,
            'task_added': task_added,
            'solved': solved,
        },
        context_instance=RequestContext(request),
    )
