from __future__ import print_function

import logging
from datetime import datetime

from django.contrib.auth import login
from django.core.cache import cache
from django.dispatch import receiver
from registration.backends.default import DefaultBackend
from registration.signals import user_activated

FINAL_URL_CACHE_PREFIX = '@final-url-'

logger = logging.getLogger('skoljka.registration')


class Backend(DefaultBackend):
    """Cache registration final url.

    We use the cache deliberately to avoid databases saves and to automatically
    delete the final_url information after some time.

    Other option would be to send the final url through the activation link,
    but that doesn't seem to be possible with the current implementation of
    django-registration...
    """

    def register(self, request, **kwargs):
        """Intercept new_user from the original `register` method and save the
        final_url into the cache."""
        new_user = super(Backend, self).register(request, **kwargs)
        final_url = request.POST.get('final_url', '/')
        # Forget the final_url after 5 minutes.
        cache.set(FINAL_URL_CACHE_PREFIX + str(new_user.id), final_url, 300)
        # Also, log that a new user was created.
        logger.info("New user id={} final_url={}".format(new_user.id, final_url))
        return new_user

    def get_final_url(self, request):
        """Read final_url from the cache."""
        if not request.user.is_authenticated():
            return '/'
        final_url = cache.get(FINAL_URL_CACHE_PREFIX + str(request.user.id))
        return final_url or '/'


@receiver(user_activated)
def _automatically_login_new_user(sender, user, request, **kwargs):
    if request.user.is_authenticated():
        return
    final_url = cache.get(FINAL_URL_CACHE_PREFIX + str(user.id))
    if final_url is not None:
        # Just in case, check both cache and date_joined.
        if (datetime.now() - user.date_joined).total_seconds() < 300:
            # FIXME: This is a hack!
            # http://stackoverflow.com/questions/6034763/django-attributeerror-user-object-has-no-attribute-backend-but-it-does
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
