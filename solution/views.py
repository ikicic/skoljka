from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from task.models import Task
from solution.models import Solution
from mathcontent.forms import MathContentForm


#TODO: dogovoriti se oko imena ove funkcije, pa i template-a
#TODO(ikicic): sto ako forma nije valid?
@login_required
def submit(request, task_id=None, solution_id=None):
    if solution_id:
        solution = get_object_or_404(Solution, pk=solution_id)
        task = solution.task
        math_content = solution.content
    elif task_id:
        task = get_object_or_404(Task, pk=task_id)
        solution = Solution(task=task, author=request.user)
        math_content = None
    else:
        raise Http404()
    
    if request.method == 'POST':
        math_content_form = MathContentForm(request.POST, instance=math_content)
        if math_content_form.is_valid():
            math_content = math_content_form.save()
            solution.content = math_content
            solution.save()
            task.solved_count = Solution.objects.values("author__id").filter(task=task).distinct().count()
            task.save()
            return HttpResponseRedirect("/solution/%d/" % (solution.id,))
        
    return render_to_response('solution_submit.html', {
        'form': MathContentForm(instance=math_content),
        'task': task,
        'action_url': request.path,
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
        L = L.filter(task=task)
    if user_id is not None:
        user = get_object_or_404(User, pk=user_id)
        L = L.filter(author=user)
    L = L.select_related('author', 'content', 'task')

    return render_to_response('solution_list.html', {
            'solutions': L.order_by('-id'),
            'task': task,
            'user': user,
        },  context_instance=RequestContext(request),
    )

def get_user_solved_tasks(user):
    if not user.is_authenticated():
        return None
    return Solution.objects.values_list("task__id", flat=True).filter(author=user).distinct()
