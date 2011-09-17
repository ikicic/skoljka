# Create your views here.

from django import forms
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from task.models import Task
from mathcontent.models import MathContentText
from django.contrib.auth.models import User
from solution.models import Solution


class SubmitForm(forms.Form):
    content = forms.CharField(min_length=1, max_length=2000, widget=forms.Textarea)

@login_required
def submit(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    if request.method == 'POST':
        form = SubmitForm(request.POST)
        if form.is_valid():
            content = MathContentText( text=form.cleaned_data['content'] )
            content.save()
            x = Solution( task=task, author=request.user, content=content )
            x.save()
            return HttpResponseRedirect("/solution/%d/" % ( x.id, ))
    else:
        form = SubmitForm()
        
    return render_to_response('solution_submit.html', {
        'form': form,
        'task': task,
        },
        context_instance=RequestContext(request),
    )
    
def solutionList(request, task_id=None, user_id=None):
    # TODO(ikicic) probaj bez .all()
    L = Solution.objects.all()
    task = None
    user = None
    
    if task_id is not None:
        task = get_object_or_404(Task, pk=task_id)
        L.filter(task=task)
    if user_id is not None:
        user = get_object_or_404(User, pk=user_id)
        L.filter(author=user)
        
    return render_to_response( 'solution_list.html', {
        'solution_list': L.order_by('-id'), 
        'task': task,
        'user': user,
    })