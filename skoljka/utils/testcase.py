import inspect
import re

from django.test import TestCase as _TestCase

# TODO: Have two TestCase classes, one with DB, one without?
# See django.utils.unittest.TestCase vs django.test.unittest.TestCase.

class TestCase(_TestCase):
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
                print "Unexpected exception '{}' ({}) for test case {}.".format(
                        e, type(e), test_case)
                raise

    def assertMultilineRegex(self, text, pattern, dotall=True):
        """Assert that the given pattern does appears in the text.
        Uses dotall (. contains '\\n') by default."""
        flags = re.DOTALL if dotall else 0
        if not re.search(pattern, text, flags):
            self.fail("Pattern '{}' not found in '{}'".format(pattern, text))
