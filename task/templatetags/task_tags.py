from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe

from tags.models import TaggedItem

from solution.models import Solution

import collections

register = template.Library()

@register.inclusion_tag('inc_task_small_box.html', takes_context=True)
def task_small_box(context, task, div_class='', url_suffix='', options='', well=True):
    return {'user': context['user'], 'task': task, 'div_class': div_class, 'url_suffix': url_suffix, 'options': options, 'well': well}

@register.simple_tag(takes_context=True)
def cache_task_info(context, tasks):    
    user = context['user']
    task_content_type = ContentType.objects.get_by_natural_key(app_label="task", model="task")
    ids = [x.id for x in tasks]
    
    # ----- tags -----
    tagovi = TaggedItem.objects.filter(content_type=task_content_type, object_id__in=ids).select_related('tag')
    tags = collections.defaultdict(list)
    for x in tagovi:
        tags[x.object_id].append((x.tag.name, x.votes_sum))
        
    for task in tasks:
        task._cache_tag_set = sorted(tags[task.id])
        
    # ----- solutions ------
    if user.is_authenticated():
        solution = Solution.objects.filter(author=user, task__id__in=ids)
        sol = dict([(x.task_id, x) for x in solution])
        for task in tasks:
            task.cache_solution = sol.get(task.id)

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
