from django import forms
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from task.models import Task
from task.forms import TaskPartForm
from solution.models import Solution
from solution.views import get_user_solved_tasks
from mathcontent.forms import MathContentForm


#TODO(ikicic): sto ako forma nije valid?
@login_required
def new(request, task_id=None):
    if task_id:
        task = get_object_or_404(Task, pk=task_id)
        math_content = task.content
        edit = True
    else:
        task = math_content = None
        edit = False
        
    if request.method == 'POST':
        task_form = TaskPartForm(request.POST,instance=task)
        math_content_form = MathContentForm(request.POST,instance=math_content)
        
        if task_form.is_valid() and math_content_form.is_valid():
            task = task_form.save(commit=False)
            math_content = math_content_form.save()
            
            if not edit:
                task.author = request.user

            task.content = math_content
            task.save()
            
            # Required for django-taggit:
            task_form.save_m2m()
            
            return HttpResponseRedirect('/task/new/finish/')
 
    return render_to_response( 'task_new.html', {
                'forms': [ TaskPartForm(instance=task), MathContentForm(instance=math_content) ],
                'action_url': request.path,
            }, context_instance=RequestContext(request),
        )
    

    
def list(request):
    tasks = Task.objects.select_related('author')

    return render_to_response( 'task_list.html', {
                'tasks' : tasks,
                'submitted_tasks' : get_user_solved_tasks(request.user),
            }, context_instance=RequestContext(request),
        )
