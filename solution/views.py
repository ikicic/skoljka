from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from activity import action as _action
from task.models import Task
from solution.models import Solution, STATUS
from mathcontent.forms import MathContentForm

from skoljka.utils.decorators import response, require

# ... trenutacna implementacija rjesenja je dosta diskutabilna

# TODO: task permissions (?)
@response('solution_detail.html')
@login_required
def detail(request, solution_id):
    solution = get_object_or_404(Solution.objects.select_related('content', 'author', 'task'), id=solution_id)
    
    if solution.correctness_avg:
        ratings = solution.correctness.select_related('user')
    else:
        ratings = []
    
    return {
        'solution': solution,
        'ratings': ratings,
    }

@require(post='action')
@response()
@login_required
def mark(request, task_id):
    action = request.POST['action']
    if action not in ['official', 'blank', 'as_solved', 'todo']:
        return (403, u'Action "%s" not valid.' % action)

    task = get_object_or_404(Task, pk=task_id)
        
    if action == 'official' and task.author != request.user and not request.user.has_perm('mark_as_official_solution'):
        return (403, u'No permission to mark as official solution.')
    
    try:
        solution = Solution.objects.get(task=task, author=request.user)
        solution.status = STATUS[action]
        solution.save()
    except Solution.DoesNotExist:
        solution = Solution.objects.create(task=task, author=request.user, status=STATUS[action])

    if action != 'blank':   # not really something interesting
        # TODO: DRY!
        type = {'official': _action.SOLUTION_AS_OFFICIAL,
                'as_solved': _action.SOLUTION_AS_SOLVED,
                'todo': _action.SOLUTION_TODO,
            }
        _action.send(request.user, type[action], action_object=solution, target=task)
        
    return (response.REDIRECT, '/task/%d/' % int(task_id))


# odgovorno za official, i mijenjanje statusa iz solution -> view
@require(post='action')
@response()
@login_required
def edit_mark(request, solution_id):
    action = request.POST['action']
    solution = get_object_or_404(Solution, id=solution_id)
    if solution.author != request.user and not request.user.is_staff:
        return (403, 'Not allowed to modify this solution.')
    
    if action in ['0', '1']:
        solution.is_official = int(action)
        solution.save()
        
        # TODO: DRY!
        if action == '1':
            _action.send(request.user, _action.SOLUTION_AS_OFFICIAL, action_object=solution, target=solution.task)
        return ('/solution/%d/' % int(solution_id),)

    if action in ['blank', 'as_solved', 'todo']:
        solution.status = STATUS[action]
        solution.save()
        
        # TODO: DRY!
        if action != 'blank':
            type = {'as_solved': _action.SOLUTION_AS_SOLVED,
                    'todo': _action.SOLUTION_TODO}
            _action.send(request.user, type[action], action_object=solution, target=solution.task)
        return ('/task/%d/' % solution.task_id,)

    return (403, u'Action "%s" not valid' % action)



#TODO: provjeriti za dupla rjesenja
#TODO: dogovoriti se oko imena ove funkcije, pa i template-a
#TODO(ikicic): sto ako forma nije valid?
@login_required
@response('solution_submit.html')
def submit(request, task_id=None, solution_id=None):
    if solution_id:
        solution = get_object_or_404(Solution, pk=solution_id)
        task = solution.task
        edit = True
    elif task_id:
        task = get_object_or_404(Task, pk=task_id)
        try:
            solution = Solution.objects.get(task=task, author=request.user)
        except Solution.DoesNotExist:
            solution = Solution(task=task, author=request.user)
        edit = False
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
            if not edit:
                _action.send(request.user, _action.SOLUTION_SUBMIT, action_object=solution, target=task)
            
            task.solved_count = Solution.objects.values("author_id").filter(task=task).distinct().count()
            task.save()
            profile = request.user.get_profile()
            profile.solved_count = Solution.objects.values('task_id').filter(author=request.user).distinct().count()
            profile.save()
            
            return ("/solution/%d/" % (solution.id,),)
        
    return {
        'form': MathContentForm(instance=math_content),
        'task': task,
        'action_url': request.path,
    }

    
def _is_valid_status(status):
    if not status:
        return True
    L = status.split(',')
    return 'blank' not in L and all((x in STATUS for x in L))

@response('solution_list.html')
def solution_list(request, task_id=None, user_id=None, status=None):
    """
        Outputs list of solutions related to
        specific task if task_id is defined,
        specific user if user_id is defined.
        If some ID is not defined, skips that condition.
    """
    
    if status is None:
        status = request.GET.get('status', None)
        if status is not None and not _is_valid_status(status):
            return (response.BAD_REQUEST, 'Invalid status.')
            
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

    return {
        'filter_by_status': status,
        'solutions': L.order_by('-id'),
        'task': task,
        'author': author,
        'submitted_active': 'active' if status == [u'submitted'] else '',
    }

def get_user_solved_tasks(user):
    if not user.is_authenticated():
        return None
    return Solution.objects.values_list("task__id", flat=True).filter(author=user).distinct()
