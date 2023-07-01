from django import template
from django.conf import settings
from django.core.urlresolvers import reverse
from django.template.base import TemplateSyntaxError
from django.utils.translation import get_language
from django.utils.translation import ugettext as _
from template_preprocessor import preprocess_tag

from skoljka.base.utils import get_featured_lectures
from skoljka.search.utils import search_tasks

register = template.Library()


@register.filter
def concat(first, second):
    return unicode(first) + unicode(second)


class ConstantNode(template.Node):
    def __init__(self, value):
        self.value = value

    def render(self, context):
        value = self.value
        if isinstance(value, dict):
            current = get_language()
            try:
                value = value[current]
            except KeyError:
                value = value[None]
        assert isinstance(value, (str, unicode))
        return value


@preprocess_tag
@register.tag
def language_preference_style(*args):
    current = get_language()
    all_lang = [lang for lang, dummy in settings.LANGUAGES]
    inactive = [lang for lang in all_lang if lang != current]
    if not inactive:
        return ''
    selector = ','.join('.ctask-content .lang-{}'.format(lang) for lang in inactive)
    out = '<style>{}{{display:none;}}</style>'.format(selector)
    if isinstance(args[0], basestring):
        # Called from the template preprocessor, just return the value.
        return out
    return ConstantNode(out)


@preprocess_tag
@register.tag
def settings_constant(*args):
    """Given a string `name`, returns settings.<name>.

    After compilation of the template, this tag is completely replaced
    with the settings.<name>. That way we don't need to process these
    tags all the time, or as in the old implementation, we don't have to
    add the constants to the context.

    Implemented in a weird way because of the way preprocess_tag behaves.
    """
    if len(args) != 2:
        raise Exception("Args doesn't have two arguments??")
    if isinstance(args[0], basestring):
        # Called from the template preprocessor, just return the value.
        out = getattr(settings, args[1])
        if isinstance(out, dict):
            out = out[get_language()]
        return out
    bits = args[1].split_contents()
    if len(bits) != 2:
        raise TemplateSyntaxError("Expected only one parameter in 'settings_constant'!")
    return ConstantNode(getattr(settings, bits[1]))


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
        'title': _(title),
        'user': context['user'],
    }


@register.inclusion_tag('inc_history_select.html')
def history_select(history):
    """Show the history of given actions.

    `history` is a list of dictionaries {'title':, 'content':}.
    """
    return {'history': history}
