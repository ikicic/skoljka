"""
    Useful string operations
"""

from django.template.defaultfilters import slugify as _slugify

import re

def slugify(value):
    """
        unicodedata (lib Django's slugify is using) does not recognize
        đ and Đ, and therefore omits them. We manually replace them with
        d and D.
    """
    return _slugify(value.replace(u'đ', u'd').replace(u'Đ', u'D'))

def obfuscate_text(text):
    return re.sub('\\S', '?', text)
