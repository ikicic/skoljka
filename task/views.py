# Create your views here.
from django import forms
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from task.models import *
from task.forms import *

@login_required
def new(request):
    if request.method == 'POST':
        form_list = TaskModelFormList(request.POST)
        if form_list.is_valid():
            (task, math_content) = form_list.save(commit=False)

            math_content.save()
            task.author = request.user
            task.content = math_content
            task.save()
            
            # Required for django-taggit:
            form_list.save_m2m()
            
            return HttpResponseRedirect('/task/new/finish/')
    
    return render_to_response(
               'task_new.html', 
               {'forms': TaskModelFormList(),},
               context_instance=RequestContext(request),
           )
    
