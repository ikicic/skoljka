from django import template
from django.conf import settings
from django.template.base import TemplateSyntaxError
from django.utils.safestring import mark_safe

from skoljka.libs.decorators import response_update_cookie
from skoljka.libs.templatetags.libs_tags import generate_get_query_string
from skoljka.libs.xss import escape

from userprofile.utils import get_useroption

from datetime import datetime

register = template.Library()

# TODO: refactor UserOptions!
# view inc_task_list.html and inc_solution_list.html

def _remove_quotations(s):
    """
    Remove " or ' from the beginning and the end of the string, if present on
    both sides of the string.
    """
    if s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s

class UserOptionNode(template.Node):
    def __init__(self, value, text, is_default, class_attr):
        self.value = unicode(value)
        self.text = text
        self.is_default = is_default
        self.class_attr = class_attr

    def render(self, context):
        field_name = context._useroptions_field_name
        value = unicode(context._useroptions_value)

        kwargs = dict([(field_name, self.value)])
        class_attr = self.class_attr
        if value == self.value:
            class_attr += ' active'

        return mark_safe(u'<a href="?{}" class="btn btn-mini {}">{}</a>\n'.format(
            generate_get_query_string(context, **kwargs),
            class_attr,
            self.text,
        ))


class UserOptionsNode(template.Node):
    def __init__(self, nodelist, field_name, default_value, allowed_values, save_to):
        self.nodelist = nodelist
        self.field_name = field_name
        self.default_value = default_value
        self.allowed_values = allowed_values
        self.save_to = save_to

    def render(self, context):
        user = context['user']

        # TODO: DRY
        if isinstance(self.field_name, basestring):
            field_name = self.field_name
        else:
            field_name = self.field_name.resolve(context)

        if isinstance(self.save_to, basestring):
            save_to = self.save_to
        else:
            save_to = self.save_to.resolve(context)


        value = context['request'].GET.get(field_name, None)
        if value is not None and value in self.allowed_values:
            if user.is_authenticated():
                profile = user.get_profile()
                setattr(profile, field_name, value)
                profile.save()
            elif not settings.DISABLE_PREF_COOKIES:
                response_update_cookie(context['request'], field_name, value)
        else:
            value = get_useroption(context['request'], field_name,
                self.default_value)

        context._useroptions_field_name = field_name
        context._useroptions_value = unicode(value)
        context[save_to] = unicode(value)

        out = '<div style="float:right;padding:8px;" class="btn-group">'    \
            + self.nodelist.render(context) \
            + '</div>'
        return out


@register.tag
def useroption(parser, token):
    bits = token.split_contents()
    if len(bits) not in (3, 4, 5):
        raise TemplateSyntaxError("Two, three or four parameters expected for 'useroption'.")

    value = _remove_quotations(bits[1])
    is_default = len(bits) >= 4 and bits[3] == 'default'
    class_attr = _remove_quotations(bits[4]) if len(bits) == 5 else ''

    return UserOptionNode(value, bits[2][1:-1], is_default, class_attr)


@register.tag
def useroptions(parser, token):
    bits = token.contents.split()
    if len(bits) not in (2, 4):
        raise TemplateSyntaxError("One or three values expected for 'useroptions'.")

    nodelist = parser.parse(('enduseroptions',))
    parser.delete_first_token()

    children = nodelist.get_nodes_by_type(UserOptionNode)
    allowed_values = [x.value for x in children]
    default_value = filter((lambda x: x.is_default), children)

    field_name = bits[1]
    if field_name[0] == field_name[-1] and field_name[0] in ('"', "'"):
        field_name = field_name[1:-1]
    else:
        field_name = parser.compile_filter(field_name)

    if len(bits) == 4:
        if bits[2] != 'as':
            raise TemplateSyntaxError("Second string must be 'as' for 'useroptions'.")
        save_to = bits[3]
    else:
        save_to = field_name

    if len(default_value) != 1:
        raise TemplateSyntaxError("Exactly one 'useroption' must have 'default' parameter!")

    return UserOptionsNode(nodelist, field_name, default_value[0].value, allowed_values, save_to)

@register.inclusion_tag('registration/inc_registration_form.html')
def registration_form():
    from userprofile.forms import UserCreationForm

    return {
        'form': UserCreationForm(extra_class='input-block-level',
            placeholders=True),
    }

@register.filter
def userlink(user, what=None):
    name = None
    if what == 'full':
        name = user.get_full_name().strip()
    elif what:
        name = getattr(user, what, None)

    # full_name kao default bi stvarao gadne probleme kod PM-a
    if not name:
        name = user.username

    return mark_safe(u'<a href="/profile/%d/" title="%s">%s</a>' % (user.pk, escape(user.get_full_name()), escape(name)))

@register.simple_tag(takes_context=True)
def update_userprofile_evaluator_time(context):
    new_count = context.get('unrated_solutions_new')
    user = context['user']
    if new_count and user.is_authenticated():
        profile = user.get_profile()
        profile._dummy_update = True
        profile.eval_sol_last_view = datetime.now()
        profile.save()

    return ''
