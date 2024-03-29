import random

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils.cache import patch_response_headers
from django.views.i18n import javascript_catalog

from skoljka.base.utils import can_edit_featured_lectures
from skoljka.folder.utils import add_or_remove_folder_task
from skoljka.permissions.constants import VIEW
from skoljka.recommend.models import UserRecommendation
from skoljka.solution.models import Solution, SolutionStatus
from skoljka.task.models import Task
from skoljka.task.templatetags.task_tags import cache_task_info
from skoljka.utils.decorators import require, response


@require(post=['task_id', 'featured'])
@login_required
@response()
def featured_lecture(request):
    if not can_edit_featured_lectures(request.user):
        return (403, "Not allowed to modify featured lectures.")

    folder_id = getattr(settings, 'FEATURED_LECTURES_FOLDER_ID', None)
    if not folder_id:
        return (400, "Featured lectures not enabled.")

    featured = request.POST['featured']
    if featured not in ['yes', 'no']:
        return (400, "Argument `featured` should be 'yes' or 'no'.")

    task = get_object_or_404(Task, id=request.POST['task_id'])
    if featured == 'yes' and (task.hidden or not task.is_lecture):
        return (403, "Task hidden or not a lecture.")  # Allow to remove.

    add = True if featured == 'yes' else False
    add_or_remove_folder_task(folder_id, task.id, add)
    return (task.get_absolute_url(),)


def homepage_offline(request, recent_tasks):
    return (
        'homepage_offline.html',
        {
            'homepage': True,
            'folder_shortcut_desc': settings.FOLDER_HOMEPAGE_SHORTCUTS_OFFLINE,
            'recent_tasks': recent_tasks,
        },
    )


def homepage_online(request, recent_tasks):
    recommend = UserRecommendation.objects.raw(
        'SELECT A.id, A.task_id FROM recommend_userrecommendation A'
        '   LEFT JOIN solution_solution B'
        '       ON (A.task_id = B.task_id AND A.user_id = B.author_id)'
        '   WHERE A.user_id = {} AND (B.status IS NULL OR B.status = 0);'.format(
            request.user.id
        )
    )
    recommend = list(x.task_id for x in recommend)
    if len(recommend) > 4:
        recommend = random.sample(recommend, 4)
    else:
        recommend = []  # Simplify design, accept only if there are 4 tasks.

    todo = Solution.objects.filter(
        author=request.user, status=SolutionStatus.TODO
    ).values_list('task_id', flat=True)[:20]
    if len(todo) > 2:
        todo = random.sample(todo, 2)
    else:
        todo = []  # Simplify design, ignore if only one to do task.

    all_tasks_to_read = todo + recommend
    if all_tasks_to_read:
        all_tasks = Task.objects.select_related('content').in_bulk(all_tasks_to_read)

        recommend = [all_tasks[id] for id in recommend]
        todo = [all_tasks[id] for id in todo]

    # context, tasks
    cache_task_info({'user': request.user}, recommend + recent_tasks)

    return (
        'homepage_online.html',
        {
            'homepage': True,
            'folder_shortcut_desc': settings.FOLDER_HOMEPAGE_SHORTCUTS_ONLINE,
            'recent_tasks': recent_tasks,
            'recommend': recommend,
            'todo': todo,
        },
    )


@response()
def homepage(request):
    recent_tasks = list(
        Task.objects.for_user(request.user, VIEW)
        .select_related('content')
        .order_by('-id')[:10]
    )

    if len(recent_tasks) > 2:
        recent_tasks = random.sample(recent_tasks, 2)

    if request.user.is_authenticated():
        return homepage_online(request, recent_tasks)
    else:
        return homepage_offline(request, recent_tasks)


def cached_javascript_catalog(*args, **kwargs):
    """Wrapper around django.views.i18n.javascript_catalog which adds
    cache_timeout."""
    response = javascript_catalog(*args, **kwargs)
    patch_response_headers(response, cache_timeout=300)
    return response
