from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe

from tags.models import TaggedItem
from solution.models import Solution
from userprofile.utils import get_useroption

from task.utils import check_prerequisites_for_tasks

import collections

register = template.Library()

@register.simple_tag()
def task_link(task, tooltip=False, url_suffix=''):
    """
        Simple wrapper.
    """
    return task.get_link(tooltip=tooltip, url_suffix=url_suffix)

@register.inclusion_tag('inc_task_small_box.html', takes_context=True)
def task_small_box(context, task, div_class='', url_suffix='', options='', well=True):
    return {'user': context['user'], 'task': task, 'div_class': div_class,
        'url_suffix': url_suffix, 'options': options, 'well': well}

@register.simple_tag(takes_context=True)
def task_options_mode_check(context):
    """
        Checks if 'options' GET key is set, and available for current user.
    """
    if context['user'].is_staff:
        context['options_mode'] = 'options' in context['request'].GET
    return ''

@register.simple_tag(takes_context=True)
def task_view_type_check(context):
    """
        Used for inc_task_list.html. Use select_related('content') if showing
        the content. Checks the user options and if the 'tasks' is the queryset.
    """
    # TODO: This is temporary solution. Refactor UserOptions!
    # Takes the old value if the current request updates it.
    tasks = context['tasks']
    if hasattr(tasks, 'select_related'):
        field_name = context.get('view_type', "task_view_type")
        # 0 is list, 1 is with content, 2 is with context (two tasks per row)
        if get_useroption(context['request'], field_name) != 0:
            context['tasks'] = tasks.select_related('content')

@register.simple_tag(takes_context=True)
def cache_task_info_lite(context, tasks):
    """
        Prepares data for task list in options mode, where whole queryset
        is selected, and only basic info is visible (such as queryset length...)
    """
    ids = [x.id for x in tasks]

    check_prerequisites_for_tasks(tasks, context['user'])
    unlocked_ids = [x.id for x in tasks if not x.cache_prerequisites_met]

    # ------ context variables --------
    context['task_ids'] = ids
    context['unlocked_task_count'] = len(unlocked_ids)
    return ''


@register.simple_tag(takes_context=True)
def cache_task_info(context, tasks):
    """
        Prepares data (tags, solution status and similar) for task list.
        Usually just one page of tasks is considered.
    """
    # TODO: cache_task_info util method that takes user, not context.
    user = context['user']
    task_content_type = ContentType.objects.get_by_natural_key(app_label="task", model="task")
    ids = [x.id for x in tasks]

    # ----- tags -----
    tagovi = TaggedItem.objects.filter(content_type=task_content_type,
        object_id__in=ids).select_related('tag')
    tagged_items = collections.defaultdict(list)
    for x in tagovi:
        tagged_items[x.object_id].append(x)

    for task in tasks:
        task._cache_tagged_items = sorted(tagged_items[task.id],
            key=lambda x: (x.tag.name, x.votes_sum))

    # ----- solutions ------
    if user.is_authenticated():
        solutions = Solution.objects.filter(author=user, task_id__in=ids)
        solutions = {x.task_id: x for x in solutions}
        for task in tasks:
            task.cache_solution = solutions.get(task.id)

    check_prerequisites_for_tasks(tasks, user)

    # ----- folder edit -----
    if user.is_authenticated():
        folder = user.profile.selected_folder
        if folder is not None:
            selected_tasks = folder.tasks.filter(id__in=ids).values_list('id', flat=True)
            for task in tasks:
                task.is_in_folder = task.id in selected_tasks


    # ------ context variables --------
    context['task_ids'] = ids
    return ''
