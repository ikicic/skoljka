"""Useful string operations"""

from django.conf import settings
from django.template.defaultfilters import slugify as _slugify

import os
import re

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


def join_urls(a, b):
    """
    Join two URLs making sure there is exactly one slash between them.
    urlparse.urljoin doesn't work well with regex URLs user for views.
    """
    if not a or not b:
        return a + b
    if a[-1] == '/': a = a[:-1]
    if b[0] == '/': b = b[1:]
    return a + '/' + b


def media_path_to_url(path):
    """Get the URL for the given media file."""
    return settings.MEDIA_URL + path[len(settings.MEDIA_ROOT) + 1:]


def obfuscate_text(text):
    return re.sub('\\S', '?', text)


def slugify(value):
    """
        unicodedata (lib Django's slugify is using) does not recognize
        đ and Đ, and therefore omits them. We manually replace them with
        d and D.
    """
    return _slugify(value.replace(u'đ', u'd').replace(u'Đ', u'D'))


def startswith_ex(T, start, string):
    """As startswith, but with a specified start."""
    return T[start:start + len(string)] == string
