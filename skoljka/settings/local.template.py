# coding=utf-8
# local.py is ignored by git!

import datetime

######################################
# General
######################################

# (REQUIRED) Full project (repository) path. For example:
#   PROJECT_ROOT = 'C:/dev/skoljka/skoljka'
#   PROJECT_ROOT = '/home/user/projects/skoljka/skoljka/'
PROJECT_ROOT = '/app'  # <-- if using docker container

ADMINS = (
    #    ('Pajo Patak', 'pajopatak@gmail.com'),
)

MANAGERS = ADMINS

# If docker is used, automatically filled by docker/build_internal.sh.
SECRET_KEY = 'KEY_SHOULD_BE_SOMETHING_COMPLICATED'  # (REQUIRED)


def _get_mysql_options():
    # TODO: Investigate which engine to use -- MyISAM or InnoDB
    # Different engines for different tables might cause problems to
    # foreign key relations.
    import subprocess

    version = subprocess.check_output(['mysql', '--version'])
    if ' 5.5.' in version:
        return {'init_command': 'SET storage_engine=MyISAM;'}
    else:  # 5.7+
        return {'init_command': 'SET default_storage_engine=MyISAM;'}


INTERNAL_IPS = ('127.0.0.1',)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'OPTIONS': _get_mysql_options(),
        'NAME': 'skoljka',  # (REQUIRED) enter database name here
        'USER': 'root',  # (REQUIRED) enter mysql username here
        'PASSWORD': '',  # (REQUIRED) enter password here
        'HOST': 'localhost',
        'PORT': '',
    }
}

DEBUG = True
TEMPLATE_DEBUG = DEBUG
ENABLE_DEBUG_TOOLBAR = True  # Works only if DEBUG is True.
MATHCONTENT_DEBUG = False  # Not dependent on DEBUG.
TEST_MODE = False
TEST_SITE_DOMAIN = 'localhost:8000'  # Used by reset_testdb.
TEST_SITE_NAME = 'localhost:8000'  # Used by reset_testdb.

# Set this if latex is not in PATH
# LATEX_BIN_DIR = 'C:\\Program Files\\texlive\\2011\\bin\\win32\\'

# Use this for development:
# EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
# EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
# EMAIL_FILE_PATH = os.path.join(PROJECT_ROOT, 'local', 'email')

EMAIL_HOST = ''
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 0

REGISTRATION_CONTACT_EMAIL = 'skoljka@skoljka.org'

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
    (4, u"Srednja \u0161kola 4. razred", 'ss4'),
    (3, u"Srednja \u0161kola 3. razred", 'ss3'),
    (2, u"Srednja \u0161kola 2. razred", 'ss2'),
    (1, u"Srednja \u0161kola 1. razred", 'ss1'),
]

# + is replaced with the appropriate tag from school class info
FOLDER_HOMEPAGE_SHORTCUTS_ONLINE = [
    'drz,+',
    'zup,+',
    'opc,+',
    'IMO',
    'shortlist',
    'MEMO',
]
FOLDER_HOMEPAGE_SHORTCUTS_OFFLINE = ['IMO', 'shortlist', 'MEMO']
FOLDER_INLINE_YEAR_COUNT = 10

######################################
# Registration challenges
######################################

REGISTRATION_CHALLENGES = [
    (r'1 + \sqrt{4} =', '3'),
    (r'2 + \sqrt{4} =', '4'),
    (r'3 + \sqrt{4} =', '5'),
    (r'4 + \sqrt{4} =', '6'),
    (r'5 + \sqrt{4} =', '7'),
    (r'6 + \sqrt{4} =', '8'),
    (r'7 + \sqrt{4} =', '9'),
]

######################################
# Other
######################################

COMPETITION_URLS = {  # no leading slashes!
    # 1: 'marinada/',
}

COMPETITION_SPECIAL_URLS = {
    # 1: [(r'something1/', view1), (r'something2/', view2)],
}

COMPETITION_MANUAL_GRADING_TAG = 'MANUAL'

DISABLE_PREF_COOKIES = True

if TEST_MODE and 'test' in DATABASES['default']['NAME']:
    EXTRA_HEADER_TOP = '''
        <div style="text-align: center; background-color: orange;">
            This is EXTRA_HEADER_TOP.
            Sign in as:
            <form action="/test/login/?revisit=1" method="POST" style="display: inline;">
                <input type="submit" name="username" value="moderator0">
                <input type="submit" name="username" value="competitor0">
            </form>
        </div>
    '''
else:
    EXTRA_HEADER_TOP = '''
        <div style="text-align: center; background-color: orange;">
            This is EXTRA_HEADER_TOP.
        </div>
    '''

EXTRA_MENU_TOP = "--EXTRA_MENU_TOP--"
# OR
EXTRA_MENU_TOP = {
    'hr': "--EXTRA_MENU_TOP--",
    None: "--default language EXTRA_MENU_TOP--",
}

LECTURES_FOLDER_URL = "/folder/<ID NOT SET>/"
FEATURED_LECTURES_FOLDER_ID = None

FOLDER_PATH_MIGRATIONS = [
    # ('oldpath', 'newpath'),
]

# Competition/course taking longer than the given thresholds will use
# unlock_days and close_days instead of unlock_minutes and close_minutes.
USE_DAYS_FOR_CHAIN_TIME_THRESHOLD = datetime.timedelta(hours=36)
