#!/usr/bin/env python

from BaseHTTPServer import BaseHTTPRequestHandler

orig = BaseHTTPRequestHandler.address_string
mapping = {}

def decorated(self, *args, **kwargs):
    if self.client_address not in mapping:
        mapping[self.client_address] = orig(self, *args, **kwargs)
    return mapping[self.client_address]

BaseHTTPRequestHandler.address_string = decorated

from django.core.management import execute_manager

try:
    import skoljka.settings  # Assumed to be in the same directory.
except ImportError:
    import sys

    sys.stderr.write(
        "Error: Can't find the file 'skoljka/settings.py' in the "
        "directory containing %r. It appears you've customized things.\n"
        "You'll have to run django-admin.py, passing it your settings "
        "module.\n(If the file settings.py does indeed exist, "
        "it's causing an ImportError somehow.)\n" % __file__
    )
    sys.exit(1)

if __name__ == '__main__':
    execute_manager(skoljka.settings)
