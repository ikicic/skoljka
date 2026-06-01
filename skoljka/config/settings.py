from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Local settings (secrets, DB config, DEBUG, etc.)
# Copy local.template.py to local.py and fill in values.
from skoljka.config.local import *  # noqa: F401, F403

INSTALLED_APPS = [
    "skoljka.apps.core",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "skoljka.apps.groups",
    "skoljka.apps.accounts",
    "skoljka.apps.content",
    "skoljka.apps.tags",
    "skoljka.apps.sources",
    "skoljka.apps.problems",
    "skoljka.apps.tracking",
    "skoljka.apps.lists",
    "skoljka.apps.news",
    "skoljka.apps.search",
    "skoljka.apps.importer",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ENABLE_DEBUG_TOOLBAR = DEBUG and globals().get("ENABLE_DEBUG_TOOLBAR", True)
if ENABLE_DEBUG_TOOLBAR:
    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.insert(
        MIDDLEWARE.index("django.middleware.common.CommonMiddleware") + 1,
        "debug_toolbar.middleware.DebugToolbarMiddleware",
    )
    INTERNAL_IPS = globals().get("INTERNAL_IPS", ["127.0.0.1", "::1"])

ROOT_URLCONF = "skoljka.config.urls"

# We use PythonJSX for rendering, but keep the Django template engine
# for the built-in admin.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "skoljka.config.wsgi.application"

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "skoljka.apps.accounts.backends.EmailOrUsernameBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", "English"),
    ("hr", "Hrvatski"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
REGISTRATION_MATH_CHALLENGE_DIR = MEDIA_ROOT / "registration_challenges"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Use the minified bundle in production (`make build-prod`).
STATIC_CSS_MAIN = "css/main.min.css" if not DEBUG else "css/main.css"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Upload caps (staff import uploads PDFs up to 50 MB).
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024

# Transcription pipeline.
TRANSCRIPTION_PRIVATE_DIR = BASE_DIR / "private" / "transcription"
TRANSCRIPTION_TTL_DAYS = 7
TRANSCRIPTION_ZOMBIE_MINUTES = 15
TRANSCRIPTION_OCR_MODEL = "mistral-ocr-latest"
TRANSCRIPTION_CHAT_MODEL = "anthropic/claude-sonnet-4-20250514"
TRANSCRIPTION_TAG_SUGGESTION_MODEL = TRANSCRIPTION_CHAT_MODEL

# External tool execution. Direct mode runs subprocesses locally. Worker mode
# sends allowlisted commands to the Docker worker over HTTP.
EXTERNAL_WORKER_HOST_ROOT = BASE_DIR
EXTERNAL_WORKER_CONTAINER_ROOT = Path("/app")
EXTERNAL_WORKER_TMP_DIR = BASE_DIR / "worker-files"
