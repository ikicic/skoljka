import functools

from django.conf import settings

IS_TESTDB = 'test' in settings.DATABASES['default']['NAME'] and getattr(
    settings, 'TEST_MODE', False
)


def assert_testdb(func):
    """View decorator that checks that the TEST_MODE is True and that the
    database is a test database."""

    def inner(*args, **kwargs):
        if not IS_TESTDB:
            raise Exception("a test function called from outside of tests!")
        return func(*args, **kwargs)

    return functools.wraps(func)(inner)
