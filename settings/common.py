#!/usr/bin/env python

import sys
import os.path

from local import *

######################################
# GENERAL
######################################

SITE_NAME = os.path.basename(PROJECT_ROOT)
LIB_ROOT = os.path.normpath(os.path.join(PROJECT_ROOT, 'lib'))
LOCAL_DIR = os.path.normpath(os.path.join(PROJECT_ROOT, 'local'))
SECRET_FILE = os.path.normpath(os.path.join(LOCAL_DIR, 'SECRET'))
DEBUG_TOOLBAR_ROOT = os.path.normpath(
    os.path.join(LIB_ROOT, 'django_debug_toolbar'))

sys.path.append(LIB_ROOT)
sys.path.append(DEBUG_TOOLBAR_ROOT)

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Zagreb'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
#LANGUAGE_CODE = 'en-us'
LANGUAGE_CODE = 'hr'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.normpath(os.path.join(LOCAL_DIR, 'media'))

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to. Don't put
# anything in this directory yourself; store your static files in apps' static/
# subdirectories and in STATICFILES_DIRS.
STATIC_ROOT = os.path.normpath(os.path.join(LOCAL_DIR, 'static'))

# URL prefix for static files.
STATIC_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.contrib.messages.context_processors.messages",
    "django.core.context_processors.request",
    "userprofile.context_processors.userprofile",
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',

# this searches for files in <app>/templates
    'django.template.loaders.app_directories.Loader',

#     'django.template.loaders.eggs.Loader',
)

#ROOT_URLCONF = SITE_NAME.lower() + '.urls'
ROOT_URLCONF = 'urls'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',

# this searches for static files in <appname>/static
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',

    #'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.normpath(os.path.join(PROJECT_ROOT, 'templates')),
)

AUTH_PROFILE_MODULE = 'userprofile.UserProfile'

INTERNAL_IPS = ('127.0.0.1',)

# Where the loging happens
LOGIN_URL = '/accounts/login/'

# Where is a user redirected after a successful log in
LOGIN_REDIRECT_URL = '/'



######################################
# Middleware
######################################

MIDDLEWARE_CLASSES = (
#    'johnny.middleware.LocalStoreClearMiddleware', # Do we need this?
    'johnny.middleware.QueryCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
#    'sentry.client.middleware.Sentry404CatchMiddleware',
#    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django_sorting.middleware.SortingMiddleware',
    'pagination.middleware.PaginationMiddleware',
)

######################################
# Installed apps
######################################

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
#    'debug_toolbar',
    'django_sorting',
    'pagination',
    'pipeline',
    'registration',
#    'sentry',
#    'sentry.client',
    'taggit',
    'template_preprocessor',

    'activity',
    'base',
    'folder',
    'mathcontent',
    'permissions',
    'pm',
    'post',
    'rating',
    'recommend',
    'tags',
    'task',
    'search',
    'solution',
    'usergroup',
    'userprofile',
    'utils',
)

######################################
# Logging
######################################

# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.

# TODO: Finish this. Admin emails are still not being sent!
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
#        'sentry': {
#            'level': 'DEBUG',
#            'class': 'sentry.client.handlers.SentryHandler',
#            'formatter': 'verbose'
#        },
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
        'console': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
#            'handlers': ['sentry'],
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
#        'sentry.errors': {
#            'level': 'DEBUG',
#            'handlers': ['console'],
#            'propagate': False,
#        },
    },
}

######################################
# johnny-cache
######################################
# Make sure all raw update/insert queries invalidate this cache!

JOHNNY_MIDDLEWARE_KEY_PREFIX = 'jCS'

# For some reason, cache did not work with the default value.
JOHNNY_MIDDLEWARE_SECONDS = 7 * 86400

# Looks like it is not smart to use blacklist at all, because johnny-cache
# won't cache the query if any of its tables are in the blacklist. For example,
# putting search_searchcacheelement into the blacklist would disable caching
# of all queries like folder.get_queryset with permission check.
# MAIN_IN_BLACKLIST = (...)

######################################
# django-registration
######################################

ACCOUNT_ACTIVATION_DAYS = 7

######################################
# django-template-preprocessor
######################################

# https://docs.djangoproject.com/en/dev/ref/settings/#languages
gettext_dummy = lambda s: s

# Define languages -> otherwise templates will be compiled in all possible languages
LANGUAGES = (
     # ('en', gettext_dummy('English')),
     ('hr', gettext_dummy('Croatian')),
)

MEDIA_CACHE_DIR = os.path.normpath(os.path.join(MEDIA_ROOT, 'cache'))
MEDIA_CACHE_URL = os.path.normpath(os.path.join(MEDIA_URL, 'cache'))
TEMPLATE_CACHE_DIR = os.path.normpath(os.path.join(LOCAL_DIR, 'templates', 'cache'))

# Wrap template loaders
if not DEBUG:
    TEMPLATE_LOADERS = (
        ('template_preprocessor.template.loaders.PreprocessedLoader',
            TEMPLATE_LOADERS
        ),
    )
## Template preprocessor for now completely disabled in debug mode. If there
## will be any need to change this, please make it as an option.
## (add a bool constant to local.py and local.template.py)
# else:
#     TEMPLATE_LOADERS = (
#         ('template_preprocessor.template.loaders.ValidatorLoader',
#         #('template_preprocessor.template.loaders.RuntimeProcessedLoader',
#             TEMPLATE_LOADERS
#         ),
#     )

# Enabled modules of the template preprocessor
TEMPLATE_PREPROCESSOR_OPTIONS = {
    # Defaults settings for all application
    # NOTE: Validation is disabled as HTML5 is not supported
    '*': ('html', 'whitespace-compression', 'no-validate-html' ),

    # Override for specific applications
    ('django.contrib.admin', 'django.contrib.admindocs', 'debug_toolbar'): ('no-html',),
}

######################################
# django-pipeline
######################################

# compresses static files (css & js) on collectstatic
STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

# TODO: fix /*! */ comments, they should be uncompressed
PIPELINE_CSS_COMPRESSOR = 'utils.csscompressor.CSSCompressor'
PIPELINE_CSS = {
    'bootstrap': {
        'source_filenames': (
          'bootstrap.css',
        ),
        'output_filename': 'bootstrap.min.css',
    },
    'skoljka': {
        'source_filenames': (
          'base.css',
          'folder.css',
          'task.css',
          'solution.css',
        ),
        'output_filename': 'skoljka.min.css',
    },
}

# TODO: fix /*! */ comments, they should be preserved
PIPELINE_JS_COMPRESSOR = 'utils.jscompressor.JSCompressor'
PIPELINE_JS = {
    'jquerystuff': {
        'source_filenames': (
#          'jquery.min.js', # using cdn now
          'jquery.autocomplete.min.js',
          'jquery.form.min.js',
          'jquery.MetaData.js',
          'jquery.tools.min.js',
          'jquery.rating.pack.js',  # rating/static/
        ),
        'output_filename': 'jquerystuff.min.js',
    },
    'skoljka': {
        'source_filenames': {
            'script.js',
            'folder.js',
            'solution.js',
        },
        'output_filename': 'skoljka.min.js',
    },
}

######################################
# django-pagination
######################################

PAGINATION_DEFAULT_WINDOW = 3
