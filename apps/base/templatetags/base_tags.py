from django import template
from django.core.urlresolvers import reverse

from search.utils import search_tasks

from base.utils import get_featured_lectures

register = template.Library()

@register.filter
def concat(first, second):
    return unicode(first) + unicode(second)


@register.simple_tag
def my_url(name, *args):
    # TODO: Test this after upgrading to Django 1.5.
    # {% url %} tag calls the reverse method with kwargs={} instead of None, so
    # it doesn't work for some reason.
    return reverse(name, args=args)


@register.filter
def fix_label_colon(label):
    # TODO: remove this after Django 1.6 (?)
    return label if label[-1] == ":" else label + ":"


@register.inclusion_tag('inc_featured_lectures.html', takes_context=True)
def show_featured_lectures(context):
    return {
        'featured_lectures': get_featured_lectures(),
        'user': context['user'],
    }


@register.inclusion_tag('inc_news_list.html', takes_context=True)
def show_news(context, div_class=None, title=None):
    news = search_tasks(['news'], user=context['user'], no_hidden_check=True)
    news = news.order_by('-id')

    return {
        'news': news,
        'div_class': div_class,
        'title': title,
        'user': context['user'],
    }


@register.inclusion_tag('inc_history_select.html')
def history_select(history):
    """Show the history of given actions.

    `history` is a list of dictionaries {'title':, 'content':}.
    """
    return {'history': history}
