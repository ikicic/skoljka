import functools

from django.conf import settings

IS_TESTDB = 'test' in settings.DATABASES['default']['NAME']


def assert_testdb(func):
    """View decorator that checks that the TEST_MODE is True and that the
    database is a test database."""
    _TEST_MODE = getattr(settings, 'TEST_MODE', False)
    _IS_TESTDB = IS_TESTDB

    def inner(*args, **kwargs):
        if not _IS_TESTDB:
            raise Exception("a test function called from outside of tests!")
        if 'test' not in settings.DATABASES['default']['NAME']:
            raise Exception("inconsistent IS_TESTDB")
        if not _TEST_MODE:
            raise Exception("test API available only in test mode")
        return func(*args, **kwargs)

    return functools.wraps(func)(inner)
