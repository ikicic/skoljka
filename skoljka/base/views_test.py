from __future__ import print_function

import functools
import sys

from django.conf import settings
from django.contrib.sites.models import Site
from django.core import mail
from django.core.management import call_command
from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt

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


@csrf_exempt
@assert_testdb
def reset_testdb(request):
    """Reset the test database to the initial state.

    Applies the fixtures .json files passed through the command line."""
    if request.method == 'POST':
        print("Resetting the test database.")
        fixtures = [arg for arg in sys.argv if arg.endswith('.json')]

        # Reset mechanism used by TransactionTestCase.
        db = 'default'
        call_command('flush', verbosity=0, interactive=False, database=db)
        call_command('loaddata', *fixtures,
                     **{'verbosity': 0, 'database': db})
        assert Site.objects.count() == 1, list(Site.objects.all())
        Site.objects.update(domain=settings.TEST_SITE_DOMAIN,
                            name=settings.TEST_SITE_NAME)

    return HttpResponse("reset_testdb\nrequest.method={}".format(request.method))


@assert_testdb
def get_latest_email(request):
    outbox = getattr(mail, 'outbox', [])
    if not outbox:
        raise Http404()
    return HttpResponse(outbox[-1].message())
