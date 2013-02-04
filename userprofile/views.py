from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Group
from django.db.models import Max, Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from userprofile.forms import UserCreationForm, UserEditForm, UserProfileEditForm
from userprofile.models import UserProfile

from recommend.models import UserTagScore
from solution.models import STATUS
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
    if request.user.is_authenticated() and request.user.pk == pk:
        user = request.user
    else:
        user = get_object_or_404(User.objects.select_related('profile'), pk=pk)    

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

    if not request.user.is_authenticated():
        visible_groups = user.groups.exclude(name=user.username).filter(data__hidden=False).select_related('data')
    elif request.user.id == pk:
        visible_groups = user.groups.exclude(name=user.username).select_related('data')
    else:
        # TODO: staviti da se vide i zajednicke skrivene grupe
        visible_groups = user.groups.exclude(name=user.username).filter(data__hidden=False).select_related('data')
        
    tags = UserTagScore.objects.filter(user=user).select_related('tag').order_by('-cache_score')[:10]
    
    
    # task lists
    # TODO: permissions
    todo = user.solution_set.filter(status=STATUS['todo'])  \
        .select_related('task').order_by('-date_created')[:10]
    solved = user.solution_set.filter(status__in=[STATUS['as_solved'],
        STATUS['submitted']]).select_related('task').order_by('-date_created')[:10]
    task_added = Task.objects.filter(author=user, hidden=False).order_by('-id')[:10]
    
    
    
    return render_to_response('profile_detail.html', {
        'profile': user,
        'distribution': distribution,
        'visible_groups': visible_groups.distinct(),
        'tags': tags,
        'todo': todo,
        'task_added': task_added,
        'solved': solved,
    }, context_instance=RequestContext(request))


# deprecated?
@permission_required('task.add_advanced')
def refresh_score(request):
    s = Solution.objects.values('author', 'task').annotate(Max('correctness_avg'))

    # ... nedovrseno ...
    
    return render_to_response('profile_refresh_score.html', {
        'solutions': s,
    }, context_instance=RequestContext(request))


# DEPRECATED, to delete
# TODO: provjeriti postoji li grupa s tim imenom
def register(request):
    if 'next' in request.REQUEST: 
        next_url = request.REQUEST['next']
    else:
        next_url = '/register/complete/'

    if request.method == "POST":
        user_form = UserCreationExtendedForm(request.POST)
        profile_form = UserProfileForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()

            # one member Group for each User
            group = Group(name=user.username)
            group.save()

            profile = profile_form.save(commit=False)
            profile.user = user
            profile.private_group = group
            profile.save()
            
            user.groups.add(group)
            
            username = user_form.cleaned_data['username']
            password = user_form.cleaned_data['password1']
            user = authenticate(username=username, password=password)
            
            if user is not None and user.is_active:
                login(request, user)
                return HttpResponseRedirect(next_url)
    else:
        user_form = UserCreationExtendedForm()
        profile_form = UserProfileForm()
    
    return render_to_response(
        'register.html',
        {'forms': [ user_form, profile_form ], 'next': next_url},
        context_instance=RequestContext(request)
    )

