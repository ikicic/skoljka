from django import template
from django.conf import settings
from django.core import urlresolvers
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.safestring import mark_safe

from userprofile.models import UserProfile
from skoljka.libs.decorators import cache_function

from tags.models import Tag, TaggedItem, VOTE_WRONG, \
    CACHE_TAGS_AUTOCOMPLETE_JS_SRC
from tags.utils import get_object_tagged_items

from hashlib import sha1
import os, codecs, re

register = template.Library()

@register.simple_tag(takes_context=True)
def tag_list(context, owner, plus_exclude=None):
    # TODO: make this contenttype-independent (look at last line)
    # TODO: memcache this

    if plus_exclude is not None:
        add = u','.join(plus_exclude)
        plus_exclude_lower = [x.lower() for x in plus_exclude]
    else:
        add = u''
        plus_exclude_lower = []

    no_plus = u'<a href="/search/?q=%(fulltag)s"%(class)s data-votes="%(votes)s">%(tag)s</a>'
    plus = no_plus + u'<a href="/search/?q=' + add + ',%(tag)s"%(class)s>+</a>'

    user = context['user']
    show_hidden_option = user.is_authenticated() and user.get_profile().show_hidden_tags
    if show_hidden_option == UserProfile.HIDDEN_TAGS_SHOW_IF_SOLVED:
        solution = getattr(owner, 'cache_solution', None)
        show_hidden = solution and solution.is_solved()
    else:
        show_hidden = show_hidden_option == UserProfile.HIDDEN_TAGS_SHOW_ALWAYS

    v0 = []     # not hidden
    v1 = []     # hidden
    for tagged_item in get_object_tagged_items(owner):
        name, votes = tagged_item.tag.name, tagged_item.votes_sum

        format = no_plus if (not plus_exclude or name.lower() in plus_exclude_lower) else plus
        attr = {'votes': votes, 'class': '', 'fulltag': name}
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
    return mark_safe(u'<div class="tag-list" data-task="%d">%s</div>' % (
        owner.id, u"".join(v0 + v1)))


###################
## Autocomplete
###################
# Even though it is deprecated, we use this autocomplete plugin:
# http://docs.jquery.com/Plugins/Autocomplete/autocomplete
# Because it supports multiple and autofill, and it has relatively short source
# code (its only dependency is jQuery).

def generate_tags_autocomplete_js():
    """
        Generate JS file that initializes all autocomplete input tags.

        Because we need the list of all tags in each request, it wouldn't be
        good to send it every time. That's why we save them to a JS file, and
        just link it with <script> tag. To be able to force refresh the list,
        filename contains the hash of its content.

        The filename is cached in tags_tags.py

        Returns js file URL / relative file path.
    """
    print 'Refreshing tags autocomplete js...'

    names = u'","'.join(Tag.objects.values_list('name', flat=True))

    # TODO: split tags by , or similar (use only one additional char per tag)
    script = u'''
        $(function() {
            $(".ac-tags").autocomplete(
                ["%s"],
                {multiple: true, autoFill: true}
            );
        });'''

    # Remove whitespace (output file doesn't have to be pretty) and put names.
    content = re.sub(r'\s+', '', script) % names

    hash = sha1(content.encode('utf-8')).hexdigest()

    # We put it in media so that it works in debug mode also... And also because
    # it's not really static.
    filename = 'media/ac_tags.{}.js'.format(hash[:8])
    full_filename = os.path.normpath(os.path.join(settings.LOCAL_DIR, filename))

    # FIXME: what if two threads try to save the file at the same time?
    f = codecs.open(full_filename, 'w', encoding='utf-8')
    f.write(content)
    f.close()

    print 'Filename:', filename
    return '/' + filename

@register.simple_tag()
@cache_function(key=CACHE_TAGS_AUTOCOMPLETE_JS_SRC)
def tags_autocomplete_js_src():
    """
        Return filename of JS file containing list of all tags
        (for autocomplete).

        The filename is cached here.
    """
    # If cache invalidated, probably the file has to be created again.
    return generate_tags_autocomplete_js()


def _invalidate_tags_autocomplete_js(sender, **kwargs):
    cache.delete(CACHE_TAGS_AUTOCOMPLETE_JS_SRC)

post_save.connect(_invalidate_tags_autocomplete_js, sender=Tag)
post_delete.connect(_invalidate_tags_autocomplete_js, sender=Tag)

# Generate and cache immediately when Django starts.
tags_autocomplete_js_src()
