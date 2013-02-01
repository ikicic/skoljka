# local.py is ignored by git!

# Full path to project
# Examples:
#   PROJECT_ROOT = 'C:/dev/skoljka'
#   PROJECT_ROOT = '/home/user/skoljka/'

ADMINS = (
    ('Pajo Patak', 'pajopatak@gmail.com'),
)

MANAGERS = ADMINS

SECRET_KEY = ''     # secret key here

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        # TODO: Investigate which engine to use -- MyISAM or InnoDB
        # Different engines for different tables might cause problems to
        # foreign key relations.
        'OPTIONS': { 'init_command': 'SET storage_engine=MyISAM;' },
        'NAME': '',                 # enter database name here
        'USER': '',                 # enter mysql username here
        'PASSWORD': '',             # enter password here
        'HOST': 'localhost',
        'PORT': '',
    }
}

DEBUG = False
TEMPLATE_DEBUG = DEBUG

# Set this if latex is not in PATH
# LATEX_BIN_DIR = 'C:\\Program Files\\texlive\\2011\\bin\\win32\\'

EMAIL_HOST = ''
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 0

EMAIL_USE_TLS = True
SERVER_EMAIL = EMAIL_HOST_USER
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
