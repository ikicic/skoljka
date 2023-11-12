"""Useful string operations"""

import re

from django.conf import settings
from django.template.defaultfilters import slugify as _slugify


# some other name?
def G(male, female, gender):
    """
    (gender) Returns string male if user is male, female if female.
    If gender isn't given, returns both strings separated with '/'.
    """
    if gender == 'M':
        return male
    elif gender == 'F':
        return female
    return male + '/' + female


def join_urls(first, *parts):
    """
    Join two or more URLs parts, such that there is exactly one slash between
    them, and that the URL ends with a / or with a regex $.
    """
    if parts:
        first = first.rstrip('/')
        other = [part.strip('/') for part in parts]
        end = '' if other[-1].endswith('$') else '/'
        return ''.join([first, '/', '/'.join(other), end])
    else:
        if first.endswith('$') or first.endswith('/'):
            return first
        else:
            return first + '/'


def media_path_to_url(path):
    """Get the URL for the given media file."""
    return settings.MEDIA_URL + path[len(settings.MEDIA_ROOT) + 1 :]


def obfuscate_text(text):
    return re.sub('\\S', '?', text)


def slugify(value):
    """
    unicodedata (lib Django's slugify is using) does not recognize
    đ and Đ, and therefore omits them. We manually replace them with
    d and D.
    """
    return _slugify(value.replace(u'đ', u'd').replace(u'Đ', u'D'))
