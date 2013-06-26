from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Group
from django.db.models import Max, Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from userprofile.forms import UserCreationForm, UserEditForm, UserProfileEditForm
from userprofile.models import UserProfile

from permissions.constants import VIEW
from recommend.models import UserTagScore
from solution.models import Solution, STATUS
from solution.templatetags.solution_tags import cache_solution_info
from task.models import Task, DIFFICULTY_RATING_ATTRS

def new_register(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/')
    from registration.views import register as _register
    return _register(request, 'registration.backends.default.DefaultBackend', form_class=UserCreationForm)


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

    return render_to_response('profile_edit.html', {
        'forms': [form1, form2],
        'success': success,
    }, context_instance=RequestContext(request))


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
        where = '((SELECT id FROM auth_user_groups AG2 '            \
                    'WHERE AG2.group_id = auth_group.id AND AG2.user_id = {} ' \
                    'LIMIT 1)'                                      \
                ' IS NOT NULL OR usergroup_usergroup.hidden != 0)'  \
                .format(user.id)
        visible_groups = user.groups.select_related('data').extra(where=[where])

    visible_groups = visible_groups.exclude(id=user.get_profile().private_group_id)

    tags = UserTagScore.objects.filter(user=user).select_related('tag').order_by('-cache_score')[:10]


    solutions = solutions.filter(author_id=pk)  \
        .select_related('task')                 \
        .order_by('-date_created')
    todo = solutions.filter(status=STATUS['todo'])[:10]
    solved = solutions.filter(
        status__in=[STATUS['as_solved'], STATUS['submitted']])[:10]

    if pk != request.user.pk:
        # TODO: optimize, do not load unnecessary my_solution
        # (separate check_accessibility should_obfuscate?)
        cache_solution_info(request.user, solved)
        for x in solved:
            x.t_can_view, dummy = x.check_accessibility(
                request.user, x._cache_my_solution)
            print x.t_can_view, dummy

    task_added = tasks.filter(author_id=pk).order_by('-id')[:10]

    return render_to_response('profile_detail.html', {
        'profile': user,
        'distribution': distribution,
        'visible_groups': visible_groups,
        'tags': tags,
        'todo': todo,
        'task_added': task_added,
        'solved': solved,
    }, context_instance=RequestContext(request))
