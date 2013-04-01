from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from activity import action as _action
from task.models import Task
from solution.models import Solution, STATUS, _update_solved_count
from mathcontent.forms import MathContentForm

from skoljka.utils.decorators import response, require

from datetime import datetime

# ... trenutacna implementacija rjesenja je dosta diskutabilna

# TODO: task permissions (?)
@response('solution_detail.html')
@login_required
def detail(request, solution_id):
    solution = get_object_or_404(Solution.objects.select_related('content',
        'author', 'task'), id=solution_id)

    if solution.correctness_avg:
        ratings = solution.correctness.select_related('user')
    else:
        ratings = []

    return {
        'solution': solution,
        'ratings': ratings,
        'hidden': solution.should_obfuscate(request.user),
    }


def _do_mark(request, solution, task):
    """
        Update solution status:
            As Solved
            To Do
            Blank

        Or mark / unmark official flag

        Creates Solution if it doesn't exist (in that case Task is given)
    """

    action = request.POST['action']

    # check requset and privileges
    if action not in ['official0', 'official1', 'blank', 'as_solved', 'todo']:
        return (403, u'Action "%s" not valid.' % action)

    if action in ['official0', 'official1'] and task.author != request.user \
            and not request.user.has_perm('mark_as_official_solution'):
        return (403, u'No permission to mark as official solution.')

    # as_solved, todo, blank
    if solution is None:
        solution, dummy = Solution.objects.get_or_create(task=task, author=request.user)

    if solution.author != request.user and not request.user.is_staff:
        return (403, 'Not allowed to modify this solution.')


    # keep track of the number of solutions for the task
    was_solved = solution.is_solved()


    # update
    if action in ['official0', 'official1']:
        solution.is_official = action == 'official1'
    elif action in ['blank', 'as_solved', 'todo']:
        if action != 'blank':
            solution.date_created = datetime.now()
        solution.status = STATUS[action]

    solution.save()


    # log the action
    if action in ['official1', 'as_solved', 'todo']:
        type_desc = {'official1': _action.SOLUTION_AS_OFFICIAL,
                     'as_solved': _action.SOLUTION_AS_SOLVED,
                     'todo': _action.SOLUTION_TODO,
            }
        _action.replace_or_add(request.user, type_desc[action],
            action_object=solution, target=task)
    elif action == 'blank':
        _action.remove(request.user, type=_action.SOLUTION_SEND,
            action_object=solution, target=task)


    # update solved count if necessary
    delta = solution.is_solved() - was_solved
    if delta:
        _update_solved_count(delta, task, request.user.get_profile())

    return None     # ok


@require(post='action')
@response()
@login_required
def mark(request, task_id):
    """
        Called from Task view
    """
    task = get_object_or_404(Task, pk=task_id)

    # _do_mark will create Solution if it doesn't exist
    ret_value = _do_mark(request, None, task)

    return ret_value or (response.REDIRECT, '/task/%d/' % int(task_id))


@require(post='action')
@response()
@login_required
def edit_mark(request, solution_id):
    """
        Called from Solution view
    """
    solution = get_object_or_404(Solution, id=solution_id)

    ret_value = _do_mark(request, solution, solution.task)

    return ret_value or ('/task/%d/' % solution.task_id,)


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
        solution, dummy = Solution.objects.get_or_create(task=task, author=request.user)
        edit = False
    else:
        return 404

    math_content = solution.content

    if request.method == 'POST':
        math_content_form = MathContentForm(request.POST, instance=math_content)
        if math_content_form.is_valid():
            math_content = math_content_form.save()

            was_solved = solution.is_solved()

            solution.content = math_content
            solution.status = STATUS['submitted']
            solution.date_created = datetime.now()
            solution.save()
            if not edit:
                _action.replace_or_add(request.user, _action.SOLUTION_SUBMIT,
                    action_object=solution, target=task)

            # update solved count if necessary
            delta = solution.is_solved() - was_solved
            if delta:
                _update_solved_count(delta, task, request.user.get_profile())

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
        'solutions': L.order_by('-date_created'),
        'task': task,
        'author': author,
        'submitted_active': 'active' if status == [u'submitted'] else '',
    }

def get_user_solved_tasks(user):
    if not user.is_authenticated():
        return None
    return Solution.objects.values_list("task__id", flat=True).filter(author=user).distinct()
