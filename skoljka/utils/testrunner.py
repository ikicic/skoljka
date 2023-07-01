from __future__ import print_function

import os
import sys
import tempfile

from django.conf import settings
from django.test.simple import DjangoTestSuiteRunner
from django.test.utils import override_settings


def assert_empty_tmp_media_root():
    """Assert that the `settings.MEDIA_ROOT` folder is empty.

    Useful for unit tests."""
    path = settings.MEDIA_ROOT
    if os.listdir(path):
        exception = sys.exc_info()[1]
        print("\nERROR: Temporary media folder '{}' not empty!".format(path))
        for root, dirs, files in os.walk(path):
            print(root, dirs, files)
        # TODO Python 3: try to enable this raise always. Python 2
        # doesn't seem to have nested exceptions. Check what happens
        # with e.g. attachments test breaking in the middle.
        if exception is None:
            raise Exception("Temporary media folder not empty.")


# https://www.caktusgroup.com/blog/2013/06/26/media-root-and-django-tests/
class TemporaryMediaRootRunner(DjangoTestSuiteRunner):
    """Custom runner that runs all tests with a temporary MEDIA_ROOT folder.

    The folder is destroyed at the end of the run.
    """

    def setup_test_environment(self):
        super(TemporaryMediaRootRunner, self).setup_test_environment()
        self.tmp_media_root = tempfile.mkdtemp(suffix='skoljka_test_media')
        self.tmp_settings = override_settings(MEDIA_ROOT=self.tmp_media_root)
        self.tmp_settings.enable()

    def teardown_test_environment(self):
        super(TemporaryMediaRootRunner, self).teardown_test_environment()
        assert settings.MEDIA_ROOT == self.tmp_media_root
        assert_empty_tmp_media_root()
        os.rmdir(self.tmp_media_root)
        self.tmp_media_root = None

        self.tmp_settings.disable()
        self.tmp_settings = None
