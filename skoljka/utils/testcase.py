from __future__ import print_function
import inspect
import re

from django.http import HttpResponse
from django.test import SimpleTestCase as _SimpleTestCase
from django.test import TestCase as _TestCase
from django.test.client import Client

from skoljka.utils.testrunner import assert_empty_tmp_media_root

class SimpleTestCase(_SimpleTestCase):
    def assertMultipleEqualOrRaise(self, func, tests):
        # test_case = (arg1, arg2, ..., argN, expected_value_or_exception)
        for test_case in tests:
            expected = test_case[-1]
            args = test_case[:-1]
            try:
                if inspect.isclass(expected) and \
                        issubclass(expected, Exception):
                    self.assertRaises(expected, func, *args)
                else:
                    self.assertEqual(func(*args), expected)
            except Exception as e:
                print("Unexpected exception '{}' ({}) for test case {}.".format(
                        e, type(e), test_case))
                raise

    def assertMultilineRegex(self, text, pattern, dotall=True):
        """Assert that the given pattern does appears in the text.
        Uses dotall (. contains '\\n') by default."""
        flags = re.DOTALL if dotall else 0
        if not re.search(pattern, text, flags):
            self.fail("Pattern '{}' not found in '{}'".format(pattern, text))


class TemporaryMediaRootMixin(object):
    """Mixin that verifies that the temporary MEDIA_ROOT folder is empty at the
    end of each test.
    """
    def tearDown(self):
        super(TemporaryMediaRootMixin, self).tearDown()
        assert_empty_tmp_media_root()


class TestCase(_TestCase, SimpleTestCase):
    """Customized TestCase class with helper functions."""
    def setUp(self):
        self.client = Client()
        super(TestCase, self).setUp()

    def login(self, user):
        self.assertTrue(self.client.login(username=user.username, password="a"))

    def logout(self):
        self.client.logout()

    def assertResponse(self, response, status_code=None, content=None):
        """Helper function for testing the status code and the content of a
        response."""
        self.assertIsInstance(response, HttpResponse)
        if status_code is not None and response.status_code != status_code:
            self.fail("Expected status code of {}, got {}. Content:\n{}".format(
                    status_code, response.status_code, response.content))
        if content is not None:
            self.assertMultiLineEqual(content, response.content)
