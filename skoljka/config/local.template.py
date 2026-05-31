# Copy this file to local.py and fill in the values.
# local.py is gitignored and should never be committed.

SECRET_KEY = "change-me-to-a-random-string"

DEBUG = True

ALLOWED_HOSTS: list[str] = []

# Registration challenge examples.
# Put the real challenge bank in local.py, then run:
# ./venv/bin/python manage.py render_registration_challenges
REGISTRATION_MATH_CHALLENGES = [
    {"id": "example-1", "tex": r"10 + \sqrt{400}", "answer": "30"},
    {"id": "example-2", "tex": r"2 \times 3", "answer": "6"},
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "skoljka",
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    }
}

EMAIL_BACKEND = "skoljka.utils.email_backends.PlainConsoleEmailBackend"
DEFAULT_FROM_EMAIL = "noreply@localhost"

# External tool execution. "direct" mode runs XeLaTeX, pdfLaTeX, Poppler, and
# Pandoc on the same host as Django. Markdown's Node renderer always runs in
# the Django environment because it uses the app's generated JS bundles.
EXTERNAL_PROCESS_MODE = "direct"

# For release/deployment, prefer the Docker worker so external tools are
# isolated from the web process. Start it with `cd docker && make up`.
#
# EXTERNAL_PROCESS_MODE = "worker"
# EXTERNAL_WORKER_URL = "http://127.0.0.1:8765/run"
# EXTERNAL_WORKER_TOKEN = "<long random shared secret>"
#
# The token is a shared secret between Django and the worker. Django sends it as
# an HTTP Bearer token; the worker accepts only requests with the same value.
# Set the worker-side value when starting Docker, for example:
#
#   EXTERNAL_WORKER_TOKEN="<same long random shared secret>" make up
#
# If the token is empty on both sides, the worker accepts local requests without
# authentication. Use a non-empty token in production.

# --- Production (before going live) ---
# DEBUG = False
# ALLOWED_HOSTS = ["your.domain"]
# SECRET_KEY = "<long random value, not the dev placeholder>"
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"  # or your provider
# Run: make build-prod && ./venv/bin/python manage.py collectstatic && migrate

# --- HTTPS / SSL ---
# After enabling HTTPS at Nginx/Certbot, uncomment and adjust:
# CSRF_TRUSTED_ORIGINS = ["https://your.domain"]
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_SSL_REDIRECT = True
