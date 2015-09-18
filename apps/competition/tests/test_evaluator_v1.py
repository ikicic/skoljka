from django.test import TestCase

from competition.evaluator_v1 import InvalidSolution, MixedTypes, \
        MixedPrecisions, IncorrectNumberOfElements, TooFewDecimals, \
        InvalidOfficial, UnallowedCharacter, InvalidModifiers, \
        AmbiguousNumberOrString, AmbiguousFloatOrList, SpaceSeparatedList, \
        ZeroDenominator
from competition.evaluator_v1 import Integer, Float, Fraction, List, MultiSet, \
        String
from competition.evaluator_v1 import check_result, parse_official

import inspect


class EvaluatorV1Test(TestCase):
    # TODO: create TestCaseEx or something like that.
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

    def assertVariableTypes(self, variable_types, tests):
        for test in tests:
            try:
                result = parse_official(test)
            except:
                print "Failed on the test case {}.".format(test)
                raise
            self.assertEqual(len(result), len(variable_types),
                    msg="Official: {}".format(test))
            for k in xrange(len(result)):
                self.assertIsInstance(result[k], variable_types[k],
                        msg="test={} k={} expected={} result={}".format(
                            test, k, variable_types[k], result[k]))

    def assertMultipleVariableTypesOrRaises(self, variable_types, tests):
        for test_case in tests:
            official, exception = test_case
            try:
                if exception is not None:
                    self.assertRaises(exception, parse_official, official)
                    continue

                result = parse_official(official)
                self.assertEqual(len(result), len(variable_types),
                        msg="Official: {}".format(official))
                for k in xrange(len(result)):
                    self.assertIsInstance(result[k], variable_types[k],
                            msg="official={} k={} expected={} result={}".format(
                                official, k, variable_types[k], result[k]))
            except Exception as e:
                print "Unexpected exception '{}' ({}) for test case {}.".format(
                        e, type(e), test_case)
                raise

    def test_validate_official_integer(self):
        self.assertMultipleVariableTypesOrRaises([Integer], [
            ("0", None),
            ("000", AmbiguousNumberOrString),
            ("0012", AmbiguousNumberOrString),
        ])

    def test_evaluate_integer(self):
        tests = [
            ("0", "0", True),
            ("-0", "0", True),
            ("-0", "-0", True),
            ("0", "-0", True),
            ("0", "+0", True),
            ("-0", "+0", True),
            ("+0", "-0", True),
            ("0", "0000", True),
            ("123", "123", True),
            ("123", "00123", True),
            ("-123", "-123", True),
            ("123", "-123", False),
            ("-123", "123", False),
            ("123" * 100, "123" * 100, True),
            ("123" * 100 + "100", "123" * 100 + "123", False),
            ("0", "0.00", InvalidSolution),
            ("0", "0,00", InvalidSolution),
            ("-0", "--0", InvalidSolution),
            ("0", "+-0", InvalidSolution),
            ("123", "324.4232", InvalidSolution),
            ("1231", "12 31", InvalidSolution),
            ("1231", "12.31", InvalidSolution),
            ("1231", "12,31", InvalidSolution),
        ]
        self.assertVariableTypes([Integer], [x[0] for x in tests])
        self.assertMultipleEqualOrRaise(check_result, tests)

    def test_validate_official_float(self):
        self.assertMultipleVariableTypesOrRaises([Float], [
            ("0012.23", AmbiguousNumberOrString),
            ("0012,23", AmbiguousNumberOrString),
            (".23", None),
            (",23", AmbiguousFloatOrList),
            ("23.", None),
            ("23,", AmbiguousFloatOrList),
            ("12.123", None),
            ("12,123", AmbiguousFloatOrList),
        ])

    def test_evaluate_float(self):
        tests = [
            ("0.00", "0", TooFewDecimals),
            ("0.00", ".0", TooFewDecimals),
            ("0.00", "0.000", True),
            ("0.00", "0.01", False),
            ("0.00", "0.005", False),
            ("0.00", "0.004", True),
            ("0.00", "0.0049999999999999999999", True),
            ("0.00", "-0.0049999999999999999999", True),
            ("0.00", "-0.005", False),
            ("0.53", ".53", True),
            (".53", ".53", True),
            ("-.53", "-.53", True),
            ("+.53", ".53", True),
            ("12.30", "12.3", TooFewDecimals),
            ("12.30", "12.30", True),
            ("12.30", "52.6", TooFewDecimals),
            ("12.34", "12.34", True),
            ("12.34", "12.345", False),
            ("12.34", "12.34499999999999", True),
            ("12.34", "12.33500000000001", True),
            ("12.34", "12.335", True),
            ("12.34", "12.33499999999999", False),
            ("-12.34", "-12.34", True),
            ("-12.34", "-12.345", False),
            ("-12.34", "-12.34499999999999", True),
            ("-12.34", "-12.33500000000001", True),
            ("-12.34", "-12.335", True),
            ("-12.34", "-12.33499999999999", False),
            ("-12.34", "12.34", False),
            ("12.34", "-12.34", False),
            ("12.34", "12.3", TooFewDecimals),
            ("12.34", "12.3449999999x999", InvalidSolution),
            ("12.34", "0,00,", InvalidSolution),
            ("12.34", "0.00.", InvalidSolution),
            ("12.", "12.", True),
            ("12.", "13.", False),
            ("12.", "12.4", True),
            ("12.", "12.5", False),
            ("12.", ".", InvalidSolution),
            ("12.", "-.", InvalidSolution),
            ("12.34", ".", InvalidSolution),
            ("12.34", "12", TooFewDecimals),
            ("12.34", "1234", TooFewDecimals),
            ("12.34", "adf", InvalidSolution),
        ]
        self.assertVariableTypes([Float], [x[0] for x in tests])
        self.assertMultipleEqualOrRaise(check_result, tests)

    def test_validate_official_fraction(self):
        self.assertMultipleVariableTypesOrRaises([Fraction], [
            ("0/1", None),
            ("10/5", None),
            ("123/0", ZeroDenominator),
            ("0\\1", None),
            ("10\\5", None),
            ("123\\0", ZeroDenominator),
        ])

    def test_evaluate_fraction(self):
        tests = [
            ("0/1", "0", True),
            ("7/13", "7/13", True),
            ("7\\13", "14/26", True),
            ("7/13", "7\\13", True),
            ("7/13", "13/7", False),
            ("-0/5", "+0/15", True),
            ("-3/6", "1/-2", True),
            ("-6/-3", "+2", True),
            ("-2/7", "1/0", InvalidSolution),
            ("-2/7", "1/7", False),
            ("1/2", "0.5", InvalidSolution),
            ("-2/7", "-2\\7", True),
        ]
        self.assertVariableTypes([Fraction], [x[0] for x in tests])
        self.assertMultipleEqualOrRaise(check_result, tests)

    def test_validate_official_list(self):
        self.assertMultipleVariableTypesOrRaises([List], [
            ("12,123", AmbiguousFloatOrList),
            ("12,-123", None),
            ("12,123,1234", None),
            ("12, 123", None),
            ("12,   123", None),
            ("12 123", SpaceSeparatedList),
            ("1,2,3,4.5", MixedTypes),
            ("#:1,2,3,4.5", MixedTypes),
            ("#:1,2,3,4,5", None),
            ("1.0,2.0,3.0,4.5", None),
            ("1.00,2.0,3.000,4.5123", MixedPrecisions),
            ("[123, 12, 232]", None),
            ("[123]", None),
            ("#:123", InvalidModifiers),
            ("#:[123]", InvalidModifiers),
            (u"\u0161", UnallowedCharacter),  # TODO: move to general
        ])

    def test_evaluate_list(self):
        tests = [
            ("1,2,3,4,5", "1, 2, 3, 4, 5", True),
            ("1,2,3,4,5", "1,2, 3,   4, 5", True),
            ("1,2,3,4,5", ",2,3,4,5", InvalidSolution),
            ("1,2,3,4,5", "1,2,,4,5", InvalidSolution),
            ("1,2,3,4,5", "1 2,3,4,5", InvalidSolution),
            ("1,2,3,4,5", "1, 2, 3, 4.5", InvalidSolution),
            ("1,2,3,4,5", "1, 2, 3, 4", False),
            ("#:1,2,3,4,5", "1, 2, 3, 4.5", InvalidSolution),
            ("#:1,2,3,4,5", "1, 2, 3, 4", IncorrectNumberOfElements),
            ("a, b, c, d", "a, b, c, d", True),
            ("a, b, c, d", "d, c, b, a", False),
        ]
        self.assertVariableTypes([List], [x[0] for x in tests])
        self.assertMultipleEqualOrRaise(check_result, tests)

    def test_validate_official_multiset(self):
        self.assertMultipleVariableTypesOrRaises([MultiSet], [
            ("{12}", None),
            ("#:{12}", InvalidModifiers),
            ("{12,123,1234}", None),
            ("{12, 123}", None),
            ("{12,   123}", None),
            ("{12 123}", SpaceSeparatedList),
            ("{1,2,3,4.5}", MixedTypes),
            ("#:{1,2,3,4.5}", MixedTypes),
            ("{1.0,2.0,3.0,4.5}", None),
            ("{1.00,2.0,3.000,4.5123}", MixedPrecisions),
            ("{abc,def,ghi}", None),
            ("{abc,5,ghi}", MixedTypes),
        ])

    def test_evaluate_string(self):
        tests = [
            ("00:50", "00:50", True),
            ("00:50", "0:50", False),
            ("sarma", "sarm", False),
            ("sarma", "sarma", True),
            ("sarma", "sarmaa", False),
            ("=002", "002", True),
            ("=002", "2", False),
            ("=002", "002", True),
        ]
        self.assertVariableTypes([String], [x[0] for x in tests])
        self.assertMultipleEqualOrRaise(check_result, tests)
