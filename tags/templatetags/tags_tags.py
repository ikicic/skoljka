from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe

from tags.models import Tag, TaggedItem, VOTE_WRONG

register = template.Library()

@register.simple_tag(takes_context=True)
def tag_list(context, owner, plus_exclude=None):
    # TODO: make this contenttype-independent (look at last line)
    # TODO: memcache this
    if not hasattr(owner, '_cache_tag_set'):
        #owner._cache_tag_set = [(tag.name, '?') for tag in owner.tags.order_by('-weight', 'name')]
        owner_content_type = ContentType.objects.get_for_model(owner)
        tags = TaggedItem.objects.filter(content_type=owner_content_type, object_id=owner.id).select_related('tag')
        owner._cache_tag_set = [(x.tag.name, x.votes_sum) for x in tags]

    if plus_exclude is not None:
        add = u','.join(plus_exclude)
        plus_exclude_lower = [x.lower() for x in plus_exclude]
    else:
        add = u''
        plus_exclude_lower = []

    no_plus = u'<a href="/search/?q=%(tag)s"%(class)s data-votes="%(votes)s">%(tag)s</a>'
    plus = no_plus + u'<a href="/search/?q=' + add + ',%(tag)s"%(class)s>+</a>'

    user = context['user']
    show_hidden = user.is_authenticated() and user.get_profile().show_hidden_tags

    v0 = []     # not hidden
    v1 = []     # hidden
    for name, votes in owner._cache_tag_set:
        format = no_plus if (not plus_exclude or name.lower() in plus_exclude_lower) else plus
        attr = {'votes': votes, 'class': ''}
        if name[0] != '$':
            attr['tag'] = name
        elif show_hidden:
            attr['tag'] = name[1:]
            attr['class'] = 'tag-hidden'
        else:
            continue

        if votes <= VOTE_WRONG:
            attr['class'] += ' tag-wrong'
        attr['class'] = ' class="%s"' % attr['class'].strip() if attr['class'] else ''
        
        (v0 if name[0] != '$' else v1).append(format % attr)

    # TODO: do not use model-specific names
    return mark_safe(u'<div class="tag-list" data-task="%d">%s</div>' % (owner.id, u' | '.join(v0 + v1)))

# iako je deprecated, namjerno se koristi
# http://docs.jquery.com/Plugins/Autocomplete/autocomplete
# zato sto podrzava multiple i autofill, i ima kratak js kod (ovisi samo o jqueryju)
@register.simple_tag(takes_context=True)
def tags_autocomplete_script(context):
    names = Tag.objects.values_list('name', flat=True)
    
    return u'<script>$(".ac_tags").autocomplete(["%s"],{multiple:true,autoFill:true});</script>' % u'","'.join(names)
