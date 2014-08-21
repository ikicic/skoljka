from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.inclusion_tag('inc_post_list_small.html', takes_context=True)
def show_posts_small(context, container):
    posts = container.posts \
            .select_related('author', 'content', 'last_edit_by') \
            .order_by('-date_created')
    user = context['user']
    for x in posts:
        x.cache_can_edit = x.can_edit(user, container)

    return {
        'posts': posts,
        'container': container,
        'request': context['request'],
        'user': user,
    }
