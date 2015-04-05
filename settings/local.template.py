# coding=utf-8
# local.py is ignored by git!

import os

######################################
# General
######################################

# (REQUIRED) Full project (repository) path. For example:
#   PROJECT_ROOT = 'C:/dev/skoljka/skoljka'
#   PROJECT_ROOT = '/home/user/projects/skoljka/skoljka/'

ADMINS = (
#    ('Pajo Patak', 'pajopatak@gmail.com'),
)

MANAGERS = ADMINS

SECRET_KEY = ''     # (REQUIRED) secret key here

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        # TODO: Investigate which engine to use -- MyISAM or InnoDB
        # Different engines for different tables might cause problems to
        # foreign key relations.
        'OPTIONS': { 'init_command': 'SET storage_engine=MyISAM;' },
        'NAME': '',                 # (REQUIRED) enter database name here
        'USER': '',                 # (REQUIRED) enter mysql username here
        'PASSWORD': '',             # (REQUIRED) enter password here
        'HOST': 'localhost',
        'PORT': '',
    }
}

DEBUG = False
TEMPLATE_DEBUG = DEBUG
ENABLE_DEBUG_TOOLBAR = True # Works only if DEBUG is True

# Set this if latex is not in PATH
# LATEX_BIN_DIR = 'C:\\Program Files\\texlive\\2011\\bin\\win32\\'

# Use this for development:
# EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
# EMAIL_FILE_PATH = os.path.join(PROJECT_ROOT, "local", "email")

EMAIL_HOST = ''
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 0

EMAIL_USE_TLS = True
SERVER_EMAIL = EMAIL_HOST_USER
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

######################################
# Cache
######################################

CACHES = {
    'default': {
        # 'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'OPTIONS': {
            'MAX_ENTRIES': 10000,
        },
        'TIMEOUT': 7 * 86400,
    }
}

######################################
# Extra base URLs
######################################

# List of pairs (URL regex, template path). Look at base/urls.py for more info.
# E.g. google verification code
EXTRA_BASE_URLS = []

######################################
# Folder shortcuts
######################################

USERPROFILE_SCHOOL_CLASS_INFO = [
    # Unique ID, Description, Tag
    (4, u'Srednja \u0161kola 4. razred', 'ss4'),
    (3, u'Srednja \u0161kola 3. razred', 'ss3'),
    (2, u'Srednja \u0161kola 2. razred', 'ss2'),
    (1, u'Srednja \u0161kola 1. razred', 'ss1'),
]

# + is replaced with the appropriate tag from school class info
FOLDER_HOMEPAGE_SHORTCUTS_ONLINE = ['drz,+', 'zup,+', 'opc,+', 'IMO',
    'shortlist', 'MEMO']
FOLDER_HOMEPAGE_SHORTCUTS_OFFLINE = ['IMO', 'shortlist', 'MEMO']
FOLDER_INLINE_YEAR_COUNT = 10

######################################
# Other
######################################

# Old path -> new path
FOLDER_PATH_MIGRATIONS = [
    # ('oldpath', 'newpath'),
]

DISABLE_PREF_COOKIES = True

COMPETITION_URLS = { # no leading slashes!
    # 1: 'marinada/',
}

EXTRA_HEADER_TOP = ""
