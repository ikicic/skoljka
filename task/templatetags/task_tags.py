from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe

from tags.models import TaggedItem

from solution.models import Solution

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
    return {'user': context['user'], 'task': task, 'div_class': div_class, 'url_suffix': url_suffix, 'options': options, 'well': well}

@register.simple_tag(takes_context=True)
def task_options_mode_check(context):
    """
        Checks if 'options' GET key is set, and available for current user.
    """
    if context['user'].is_staff:
        context['options_mode'] = 'options' in context['request'].GET
    return ''

@register.simple_tag(takes_context=True)
def cache_task_info_lite(context, tasks):
    """
        Prepares data for task list in options mode, where whole queryset
        is selected, and only basic info is visible (such as queryset length...)
    """
    ids = [x.id for x in tasks]

    # ------ context variables --------
    context['task_ids'] = ids
    return ''


@register.simple_tag(takes_context=True)
def cache_task_info(context, tasks):
    """
        Prepares data (tags, solution status and similar) for task list.
        Usually just one page of tasks is considered.
    """
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
        # All tasks for which solutions we are interested in.
        all_tasks = sum([x._get_prerequisites() for x in tasks], ids)
        solutions = Solution.objects.filter(author=user, task_id__in=all_tasks)
        solutions = {x.task_id: x for x in solutions}
        for task in tasks:
            task.cache_solution = solutions.get(task.id)
            task._check_prerequisites(user, solutions)

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
