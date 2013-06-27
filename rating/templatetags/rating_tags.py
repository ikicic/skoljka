from django import template
from django.utils.safestring import mark_safe
from django.contrib.contenttypes.models import ContentType

register = template.Library()

# TODO: readonly parameter (view solution)
@register.inclusion_tag('inc_rating_box.html', takes_context=True)
def rating_box(context, text, manager):
    user_vote = manager.get_vote_for_user(context['request'].user)
    return {
        'text': text,
        'm': manager,
        'user_vote': None if user_vote is None else user_vote.value
    }

@register.simple_tag
def rating_stars(manager=None, field=None, red_if_lt=0.0, value=None):
    if not field:
        field = manager.field
    if value is None:
        value = getattr(manager.instance, '%s_avg' % field.name)
    left = int(80 * value / float(field.range - 1))

    title = field.titles[int(value + 0.5)]

    # TODO: ako min ili max samo jedan div
    return mark_safe(
        u'<div class="readonly-star" style="background-position:0px %(shift)dpx;width:%(left)spx;" title="%(title)s"></div>'
        u'<div class="readonly-star" style="background-position:-%(left)spx 0px;width:%(right)spx;" title="%(title)s"></div>' % {
            'left': left, 'right': int(80 - left), 'title': title, 'shift': (-16 if value < red_if_lt else -32),
        })
