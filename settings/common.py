#!/usr/bin/env python

import sys
import os.path

from utils.generators import SecretKeyGen

PROJECT_ROOT = os.getcwd()
SITE_NAME = os.path.basename(PROJECT_ROOT)
LIB_ROOT = os.path.normpath(os.path.join(PROJECT_ROOT, 'lib'))
LOCAL_DIR = os.path.normpath(os.path.join(PROJECT_ROOT, 'local'))
SECRET_FILE = os.path.normpath(os.path.join(LOCAL_DIR, 'SECRET'))
DEBUG_TOOLBAR_ROOT = os.path.normpath(
    os.path.join(LIB_ROOT, 'django_debug_toolbar'))

sys.path.append(LIB_ROOT)
sys.path.append(DEBUG_TOOLBAR_ROOT)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # Add yourself here
    ('Bruno Rahle', 'brahle@gmail.com'),
    ('Goran Zuzic', 'zuza777@gmail.com'),
    ('Ivica Kicic', 'ivicakicic@gmail.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.normpath(os.path.join(LOCAL_DIR, 'db.sqlite')),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.normpath(os.path.join(PROJECT_ROOT, 'media'))

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to. Don't put
# anything in this directory yourself; store your static files in apps' static/
# subdirectories and in STATICFILES_DIRS.
STATIC_ROOT = os.path.normpath(os.path.join(PROJECT_ROOT, 'static'))

# URL prefix for static files.
STATIC_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '*+2=z1qx9+zm6bxuz+i&f(y*6xs9v2=alaeap3glfceof_--nm'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',

# this searches for files in <app>/templates
    'django.template.loaders.app_directories.Loader',

#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'sentry.client.middleware.Sentry404CatchMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

ROOT_URLCONF = SITE_NAME.lower() + '.urls'

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

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'debug_toolbar',
    'sentry',
    'sentry.client',
    'taggit',
    
    'base',
    'folder',
    'mathcontent',
    'task',
    'search',
    'solution',
    'userprofile',
)

# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
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
        'sentry': {
            'level': 'DEBUG',
            'class': 'sentry.client.handlers.SentryHandler',
            'formatter': 'verbose'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        '()': {
            'level': 'WARNING',
            'handlers': ['sentry'],
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}

INTERNAL_IPS = ('127.0.0.1',)

# Where the loging happens
LOGIN_URL = '/login/'

# Where is a user redirected after a successful log in
LOGIN_REDIRECT_URL = '/'


try:
    SECRET_KEY = open(SECRET_FILE).read().strip()
except IOError:
    try:
        if not os.path.exists(LOCAL_DIR):
            os.makedirs(LOCAL_DIR)
        with open(SECRET_FILE, 'w') as f:
            f.write(SecretKeyGen.generate(50))
    except IOError:
        raise Exception('Cannot open file `%s` for writing.' % SECRET_FILE)

