from django.contrib.auth import authenticate, login
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from userprofile.forms import UserCreationExtendedForm, UserProfileForm

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

