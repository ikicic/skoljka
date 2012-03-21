from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe

from tags.models import TaggedItem
from taggit.utils import parse_tags

from solution.models import Solution

import collections

register = template.Library()

@register.inclusion_tag('inc_task_small_box.html', takes_context=True)
def task_small_box(context, task, div_class='', url_suffix='', options=''):
    return {'user': context['user'], 'task': task, 'div_class': div_class, 'url_suffix': url_suffix, 'options': options}

@register.filter
def cache_additional_info(tasks, user):
    task_content_type = ContentType.objects.get_by_natural_key(app_label="task", model="task")
    ids = [x.id for x in tasks]
    
    # ----- tags -----
    tagovi = TaggedItem.objects.filter(content_type=task_content_type, object_id__in=ids).select_related('tag')
    tags = collections.defaultdict(list)
    for x in tagovi:
        tags[x.object_id].append(x.tag.name)
        
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
        
    return tasks

@register.simple_tag(takes_context=True)
def tag_list(context, task, plus_exclude=None):
    if not hasattr(task, '_cache_tag_set'):
        task._cache_tag_set = [tag.name for tag in task.tags.order_by('-weight', 'name')]

    if plus_exclude is not None:
        add = u','.join(plus_exclude)
        plus_exclude_lower = [x.lower() for x in plus_exclude]
    else:
        add = u''
        plus_exclude_lower = []

    no_plus = u'<a href="/search/?q=%(tag)s"%(hidden)s>%(tag)s</a>'
    plus = u'<a href="/search/?q=%(tag)s"%(hidden)s>%(tag)s</a> <a href="/search/?q=' + add + ',%(tag)s"%(hidden)s>+</a>'

    user = context['user']
    show_hidden = user.is_authenticated() and user.get_profile().show_hidden_tags
    
    v0 = []     # not hidden
    v1 = []     # hidden
    for tag in task._cache_tag_set:
        format = no_plus if (not plus_exclude or tag.lower() in plus_exclude_lower) else plus
        if tag[0] != '$':
            v0.append(format % {'tag': tag, 'hidden': ''})
        elif show_hidden:
            v1.append(format % {'tag': tag[1:], 'hidden': ' class="hidden_tag"'})
    return mark_safe('<div class="tag_list">%s</div>' % u' | '.join(v0 + v1))

    
@register.filter
def multiple_task_link(tasks):
    return mark_safe(u'<a href="/task/multiple/%s/">Prikaži tekstove zadataka odjednom</a>' % ','.join([str(x.id) for x in tasks]))
