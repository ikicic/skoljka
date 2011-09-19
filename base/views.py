from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

def register(request):
    if 'next' in request.REQUEST: 
        next_url = request.REQUEST['next']
    else:
        # FIXME(brahle): url here
        next_url = '/'
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            user = authenticate(username=username, password=password)
            
            if user is not None and user.is_active:
                login(request, user)
                return HttpResponseRedirect(next_url)
    else:
        form = UserCreationForm()
    return render_to_response(
        'register.html',
        {'form': form, 'next': next_url},
        context_instance=RequestContext(request)
    )
