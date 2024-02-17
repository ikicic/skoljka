"""Helper definitions for the Python2 -> Python3 transition."""

# TODO: Making flake8 happy. Remove after switching to Python 3:
unicode = type(u'')
basestring = str.__mro__[1]
long = (2 ** 128).__class__
assert 'basestring' in str(basestring)
