from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from task.models import Task
from solution.models import Solution, STATUS
from mathcontent.forms import MathContentForm

# ... trenutacna implementacija rjesenja je dosta diskutabilna


@login_required
def mark(request, task_id):
    if request.method != 'POST' or 'action' not in request.POST:
        return HttpResponseForbidden('Not valid request')

    action = request.POST['action']
    if action not in ['blank', 'as_solved', 'todo']:
        return HttpResponseForbidden(u'Action "%s" not valid' % action)

    task = get_object_or_404(Task, pk=task_id)
        
    if action == 'official' and task.author != request.user and not request.user.has_perm('mark_as_official_solution'):
        return HttpResponseForbidden(u'No permission to mark as official solution.')
    
    try:
        solution = Solution.objects.get(task=task, author=request.user)
        solution.status = STATUS[action]
        solution.save()
    except Solution.DoesNotExist:
        Solution.objects.create(task=task, author=request.user, status=STATUS[action])

    return HttpResponseRedirect('/task/%d/' % int(task_id))


# odgovorno za official, i mijenjanje statusa iz solution -> view
@login_required
def edit_mark(request, solution_id):
    if request.method != 'POST' or 'action' not in request.POST:
        raise HttpResponseForbidden('Not valid request')
    
    action = request.POST['action']
    sol = Solution.objects.filter(pk=solution_id)
    
    if action in ['0', '1']:
        sol.update(is_official=int(action))
        return HttpResponseRedirect('/solution/%d/' % int(solution_id))

    if action in ['blank', 'as_solved', 'todo']:
        sol.update(status=STATUS[action])
        solution = get_object_or_404(Solution, pk=solution_id)
        return HttpResponseRedirect('/task/%d/' % solution.task_id)

    return HttpResponseForbidden(u'Action "%s" not valid' % action)
        
   
    


#TODO: provjeriti za dupla rjesenja
#TODO: dogovoriti se oko imena ove funkcije, pa i template-a
#TODO(ikicic): sto ako forma nije valid?
@login_required
def submit(request, task_id=None, solution_id=None):
    if solution_id:
        solution = get_object_or_404(Solution, pk=solution_id)
        task = solution.task
    elif task_id:
        task = get_object_or_404(Task, pk=task_id)
        try:
            solution = Solution.objects.get(task=task, author=request.user)
        except Solution.DoesNotExist:
            solution = Solution(task=task, author=request.user)
    else:
        raise Http404()
    math_content = solution.content
    
    if request.method == 'POST':
        math_content_form = MathContentForm(request.POST, instance=math_content)
        if math_content_form.is_valid():
            math_content = math_content_form.save()
            
            solution.content = math_content
            solution.status = STATUS['submitted']
            solution.save()
            
            task.solved_count = Solution.objects.values("author_id").filter(task=task).distinct().count()
            task.save()
            profile = request.user.get_profile()
            profile.solved_count = Solution.objects.values('task_id').filter(author=request.user).distinct().count()
            profile.save()
            
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
def solution_list(request, task_id=None, user_id=None):
    L = Solution.objects.exclude(status=STATUS['blank'])
    task = None
    author = None   # 'user' is template reserved word
    
    if task_id is not None:
        task = get_object_or_404(Task, pk=task_id)
        L = L.filter(task=task)
    if user_id is not None:
        author = get_object_or_404(User, pk=user_id)
        L = L.filter(author=author)
    L = L.select_related('author', 'content', 'task')

    return render_to_response('solution_list.html', {
            'solutions': L.order_by('-id'),
            'task': task,
            'author': author,
        },  context_instance=RequestContext(request),
    )

def get_user_solved_tasks(user):
    if not user.is_authenticated():
        return None
    return Solution.objects.values_list("task__id", flat=True).filter(author=user).distinct()
