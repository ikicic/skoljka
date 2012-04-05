from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe

from tags.models import Tag

register = template.Library()

# iako je deprecated, namjerno se koristi
# http://docs.jquery.com/Plugins/Autocomplete/autocomplete
# zato sto podrzava multiple i autofill, i ima kratak js kod (ovisi samo o jqueryju)

@register.simple_tag(takes_context=True)
def tags_autocomplete_script(context):
    names = Tag.objects.values_list('name', flat=True)
    
    return u'<script>$(".ac_tags").autocomplete(["%s"],{multiple:true,autoFill:true});</script>' % u'","'.join(names)