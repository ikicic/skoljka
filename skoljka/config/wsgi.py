import os

import pythonjsx.importer

pythonjsx.importer.install()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skoljka.config.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
