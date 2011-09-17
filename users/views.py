from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

# TODO(brahle): csrf protection - verify it works
# TODO(brahle): class and not function
# TODO(brahle): change name
# TODO(brahle): move to middleware
def login_view(request):
    form = AuthenticationForm(None, request.POST or None)
    if form.is_valid():
        user = form.get_user()
        if user is not None and user.is_active:
            login(request, user)
            # TODO(brahle): change this to a view
            return HttpResponseRedirect('/')
    return render_to_response(
        'login.html', 
        {'form': form},
        context_instance=RequestContext(request)
    )
