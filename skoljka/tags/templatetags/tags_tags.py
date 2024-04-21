from __future__ import print_function

import codecs
import os
import re
from hashlib import sha1

from django import template
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.db.utils import DatabaseError
from django.utils.safestring import mark_safe

from skoljka.tags.models import CACHE_TAGS_AUTOCOMPLETE_JS_SRC, VOTE_WRONG, Tag
from skoljka.tags.utils import get_object_tagged_items, split_tags
from skoljka.userprofile.models import UserProfile
from skoljka.utils.decorators import cache_function

register = template.Library()


@register.simple_tag()
def tag_list_preview(tags):
    """Given a list or a comma-separated list of tags, just render them
    without any logic."""
    tags = split_tags(tags)

    no_plus = u'<a href="/search/?q={}">{}</a>'
    tags_html = [no_plus.format(tag, tag) for tag in tags]

    return mark_safe(
        u'<div class="tag-list preview">{}</div>'.format(u" ".join(tags_html))
    )


@register.simple_tag(takes_context=True)
def tag_list(context, owner, plus_exclude=None):
    # TODO: memcache this

    if plus_exclude is not None:
        add = u','.join(plus_exclude)
        plus_exclude_lower = [x.lower() for x in plus_exclude]
    else:
        add = u''
        plus_exclude_lower = []

    no_plus = (
        u'<a href="/search/?q=%(fulltag)s"%(class)s data-votes="%(votes)s">%(tag)s</a>'
    )
    plus = no_plus + u'<a href="/search/?q=' + add + ',%(tag)s"%(class)s>+</a>'

    user = context['user']
    show_hidden_option = user.is_authenticated() and user.get_profile().show_hidden_tags
    show_hidden = show_hidden_option == UserProfile.HIDDEN_TAGS_SHOW_ALWAYS

    content_type = ContentType.objects.get_for_model(owner)
    if content_type.app_label == 'task' and content_type.model == 'task':
        if show_hidden_option == UserProfile.HIDDEN_TAGS_SHOW_IF_SOLVED:
            # TODO: do not rely on cache_solution
            solution = getattr(owner, 'cache_solution', None)
            show_hidden = solution and solution.is_solved()

    v0 = []  # not hidden
    v1 = []  # hidden
    for tagged_item in get_object_tagged_items(owner):
        name = tagged_item.tag.name
        votes = tagged_item.votes_sum
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
        if attr['class']:
            attr['class'] = ' class="{}"'.format(attr['class'].strip())

        if not plus_exclude or name.lower() in plus_exclude_lower:
            fmt = no_plus
        else:
            fmt = plus
        (v0 if name[0] != '$' else v1).append(fmt % attr)

    # Update skoljka/tags/static/tags.js and .scss if changing this!
    return mark_safe(
        u'<div class="tag-list tag-list-tooltip" data-content-type-id="{}" '
        u'data-object-id="{}">{}</div>'.format(
            content_type.id, owner.id, u" ".join(v0 + v1)
        )
    )


###################
# Autocomplete
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
    print("Refreshing tags autocomplete js...")

    names = u'","'.join(Tag.objects.values_list('name', flat=True))

    # TODO: split tags by , or similar (use only one additional char per tag)
    script = u'''
        $(function() {
            $(".ac-tags").autocomplete(
                ["%s"],
                {
                    autoFill: true,
                    multiple: true,
                    multipleSeparator: ",[[SPACE]]",
                    noRecord: ""
                }
            );
        });'''
    # script = 'tmp="%s";'

    # Remove whitespace (output file doesn't have to be pretty) and put names.
    content = re.sub(r'\s+', '', script).replace('[[SPACE]]', ' ') % names

    hash = sha1(content.encode('utf-8')).hexdigest()

    # We put it in media so that it works in debug mode also... And also because
    # it's not really static.
    filename = 'media/ac_tags.{}.js'.format(hash[:8])
    full_filename = os.path.normpath(os.path.join(settings.LOCAL_DIR, filename))

    # FIXME: what if two threads try to save the file at the same time?
    f = codecs.open(full_filename, 'w', encoding='utf-8')
    f.write(content)
    f.close()

    print("Filename:", filename)
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
try:
    tags_autocomplete_js_src()
except DatabaseError as e:
    # Possibly the database isn't even initialized yet.
    print(e)
    print("Skipping building tags autocomplete.")
