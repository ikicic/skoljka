from django import template
from django.utils.safestring import mark_safe
from django.contrib.contenttypes.models import ContentType

register = template.Library()

# TODO: readonly parameter (view solution)
@register.simple_tag(takes_context=True)
def rating_box(context, text, manager, use_bool_design=False):
    user_vote = manager.get_vote_for_user(context['request'].user)

    _template = template.loader.get_template(
            'inc_rating_box_bool.html' if use_bool_design else
            'inc_rating_box.html')

    context.push()
    context.update({
        'text': text,
        'm': manager,
        'user_vote': None if user_vote is None else user_vote.value
    })
    result = _template.render(context)
    context.pop()
    return result

@register.simple_tag
def rating_display_bool(manager=None, field=None, red_if_lt=1.5, value=None,
        empty_if_no_votes=False):
    if not field:
        field = manager.field
    if value is None:
        value = getattr(manager.instance, '%s_avg' % field.name)

    if value == 0:
        if empty_if_no_votes:
            return ''
        title = field.titles[0]
        label = ''
    elif value < red_if_lt:
        title = field.titles[1]
        label = 'label-important'
    else:
        title = field.titles[2]
        label = 'label-success'

    if int(value) == value:
        return u'<span class="label {}">{}</span>'.format(label, title)

    return u'<span class="label {}" title="{}">{}%</span>'.format(
            label, title, int((value - 1) * 100))



@register.simple_tag
def rating_stars(manager=None, field=None, red_if_lt=0.0, value=None):
    if not field:
        field = manager.field
    if value is None:
        value = getattr(manager.instance, '%s_avg' % field.name)


    # TODO: if min or max value, output only one div.
    left = int(80 * value / float(field.range - 1))
    right = int(80 - left)
    shift = -16 if value < red_if_lt else -32
    title = field.titles[int(value + 0.5)]
    return mark_safe(
        u'<div class="readonly-star" style="background-position:'
        u'0px {}px;width:{}px;" title="{}"></div>'
        u'<div class="readonly-star" style="background-position:'
        u'-{}px 0px;width:{}px;" title="{}"></div>'.format(
            shift, left, title, left, right, title
            ))
