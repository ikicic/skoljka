"""
    Useful string operations
"""

import re

# DEPRECATED: useless, delete!
def list_strip(L, remove_empty=True):
    T = [x.strip() for x in L]
    if remove_empty:
        return filter(None, T)
    return T

def obfuscate_text(text):
    return re.sub('\\S', '?', text)
