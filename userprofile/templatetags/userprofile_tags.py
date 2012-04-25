from django import template
from django.template.base import TemplateSyntaxError
from django.utils.safestring import mark_safe

from skoljka.utils.decorators import response_update_cookie
from skoljka.utils.xss import escape

register = template.Library()

# view inc_task_list.html and inc_solution_list.html

class UserOptionNode(template.Node):
    def __init__(self, value, text, is_default):
        self.value = unicode(value)
        self.text = text
        self.is_default = is_default
        
    def render(self, context):
        # TODO: move field_name to parser (and __init__), not context
        field_name = context._useroptions_field_name
        value = unicode(context._useroptions_value)
        
        # TODO: move to utils
        # (from django-pagination/templatetags/pagination_tags.py:paginate)
        getvars = context['request'].GET.copy()
        if field_name in getvars:
            del getvars[field_name]
        if len(getvars.keys()) > 0:
            getvars = '&amp;' + escape(getvars.urlencode())
        else:
            getvars = ''
        
        return mark_safe(u'<a href="?{0}={1}{2}" class="btn btn-mini{3}">{4}</a>\n'.format(
            field_name,
            escape(self.value),
            getvars,
            ' active' if value == self.value else '',
            self.text,
        ))


class UserOptionsNode(template.Node):
    def __init__(self, nodelist, field_name, default_value, allowed_values):
        self.nodelist = nodelist
        self.field_name = field_name
        self.default_value = default_value
        self.allowed_values = allowed_values

    def render(self, context):
        user = context['user']

        value = context['request'].GET.get(self.field_name, None)
        if value is not None and value in self.allowed_values:
            if user.is_authenticated():
                setattr(user.get_profile(), self.field_name, value)
                user.get_profile().save()
            else:
                response_update_cookie(context['request'], self.field_name, value)
        elif user.is_authenticated():
            value = getattr(user.get_profile(), self.field_name)
        else:
            value = context['request'].COOKIES.get(self.field_name, self.default_value)

        context._useroptions_field_name = self.field_name
        context._useroptions_value = unicode(value)
        context[self.field_name] = unicode(value)
        print 'CONTEXT FIELDNAME', context[self.field_name]
        
        out = '<div style="float:right;padding:8px;" class="btn-group">'    \
            + self.nodelist.render(context) \
            + '</div>'
        return out


@register.tag
def useroption(parser, token):
    bits = token.split_contents()
    if len(bits) not in (3, 4):
        raise TemplateSyntaxError("Two or three parameters expected for 'useroption'.")
    is_default = len(bits) == 4 and bits[-1] == 'default'
    
    value = bits[1]
    if value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1]

    return UserOptionNode(value, bits[2][1:-1], is_default)


@register.tag
def useroptions(parser, token):
    bits = token.contents.split()
    if len(bits) != 2:
        raise TemplateSyntaxError("One value expected for 'useroptions'.")

    nodelist = parser.parse(('enduseroptions',))
    parser.delete_first_token()
    
    children = nodelist.get_nodes_by_type(UserOptionNode)
    allowed_values = [x.value for x in children]
    default_value = filter((lambda x: x.is_default), children)
    
    
    if len(default_value) != 1:
        raise TemplateSyntaxError("Exactly one 'useroption' must have 'default' parameter!")
    
    return UserOptionsNode(nodelist, bits[1][1:-1], default_value[0].value, allowed_values)
    

            
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
