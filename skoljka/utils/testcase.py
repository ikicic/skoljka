import inspect

from django.test import TestCase


class TestCaseEx(TestCase):
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
