from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Group
from django.db.models import Max
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from userprofile.forms import UserCreationExtendedForm, UserProfileForm

from rating.constants import DIFFICULTY_RATING_ATTRS

@login_required
def profile(request, pk):
    # FIXME: vide se skrivene grupe
    try:
        user = User.objects.select_related('profile').get(pk=pk)
    except:
        raise Http404
    

    user.profile.update_diff_distribution()
    distribution = user.profile.get_normalized_diff_distribution()
    if distribution:
        distribution = zip(DIFFICULTY_RATING_ATTRS['titles'], [int(x * 100) for x in distribution])
    
    return render_to_response('profile_detail.html', {
        'profile': user,
        'distribution': distribution,
    }, context_instance=RequestContext(request))


@permission_required('task.add_advanced')
def refresh_score(request):
    s = Solution.objects.values('author', 'task').annotate(Max('correctness_avg'))

    # ... nedovrseno ...
    
    return render_to_response('profile_refresh_score.html', {
        'solutions': s,
    }, context_instance=RequestContext(request))


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
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            
            # one member Group for each User
            group = Group(name=user.username)
            group.save()
            
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

