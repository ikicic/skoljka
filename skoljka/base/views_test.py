from __future__ import print_function

import sys

from django.conf import settings
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core import mail
from django.core.management import call_command
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.i18n import set_language

from skoljka.utils.testutils import assert_testdb


@assert_testdb
def get_latest_email(request):
    outbox = getattr(mail, 'outbox', [])
    if not outbox:
        raise Http404()
    return HttpResponse(outbox[-1].message())


@csrf_exempt
@assert_testdb
def login(request):
    """Sign in a user credentials."""
    for user in User.objects.all():
        print(user)
    username = request.POST.get('username')
    user = get_object_or_404(User, username=username)

    # Fake the authenticate() call.
    user.backend = settings.AUTHENTICATION_BACKENDS[0]
    auth_login(request, user)

    return HttpResponse('{"user": %d}' % user.id, mimetype='application/json')


@csrf_exempt
@assert_testdb
def logout(request):
    """Sign out the user. Silently ignored if the user is not authenticated."""
    auth_logout(request)
    return HttpResponse('{}', mimetype='application/json')


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
        call_command('loaddata', *fixtures, **{'verbosity': 0, 'database': db})
        assert Site.objects.count() == 1, list(Site.objects.all())
        Site.objects.update(
            domain=settings.TEST_SITE_DOMAIN, name=settings.TEST_SITE_NAME
        )

    return HttpResponse("reset_testdb\nrequest.method={}".format(request.method))


@csrf_exempt
@assert_testdb
def setlang(request):
    """Set the language, circumventing the CSRF check."""
    return set_language(request)
