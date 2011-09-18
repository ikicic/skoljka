from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from task.models import Task
from solution.models import Solution
from mathcontent.forms import MathContentForm

@login_required
def submit(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    if request.method == 'POST':
        form = MathContentForm(request.POST)
        if form.is_valid():
            content = form.save()
            solution = Solution(task=task, author=request.user, content=content)
            solution.save()
            return HttpResponseRedirect("/solution/%d/" % (solution.id,))
    else:
        form = MathContentForm()        
    return render_to_response('solution_submit.html', {
        'form': form,
        'task': task,
        },
        context_instance=RequestContext(request),
    )

# TODO(gzuzic): move description to docstring
# Outputs list of solution related to
#   specific task if task_id is defined
#   specific user if user_id is defined
# If some ID is not defined, skips that condition.
def solutionList(request, task_id=None, user_id=None):
    # TODO(ikicic) research .objects vs .objects.all()
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
