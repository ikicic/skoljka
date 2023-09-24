"""Helper definitions for the Python2 -> Python3 transition."""

# TODO: Making flake8 happy. Remove after switching to Python 3:
unicode = type(u'')
basestring = str.__mro__[1]
assert 'basestring' in str(basestring)
