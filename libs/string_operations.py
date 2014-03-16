"""
    Useful string operations
"""

from django.template.defaultfilters import slugify as _slugify

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

def obfuscate_text(text):
    return re.sub('\\S', '?', text)

def slugify(value):
    """
        unicodedata (lib Django's slugify is using) does not recognize
        đ and Đ, and therefore omits them. We manually replace them with
        d and D.
    """
    return _slugify(value.replace(u'đ', u'd').replace(u'Đ', u'D'))
