# XSS = Cross site scripting
# http://en.wikipedia.org/wiki/Cross_site_scripting

html_escape_table = (
    ("&", "&amp;"),  # this one must be the first
    ('"', "&quot;"),
    ("'", "&apos;"),
    (">", "&gt;"),
    ("<", "&lt;"),
)


def escape(s):
    for beg, end in html_escape_table:
        s = s.replace(beg, end)
    return s


def unescape(s):
    for i in xrange(len(html_escape_table) - 1, 0, -1):
        beg, end = html_escape_table[i]
        s = s.replace(end, beg)
    return s
