from __future__ import print_function

from skoljka.competition import evaluator_v1
from skoljka.competition.evaluator import get_sample_solution, safe_parse_descriptor
from skoljka.competition.evaluator_v1 import (
    AmbiguousFloatOrList,
    AmbiguousNumberOrString,
    Float,
    Fraction,
    IncorrectNumberOfElements,
    Integer,
    InvalidModifiers,
    InvalidSolution,
    List,
    MixedPrecisions,
    MixedTypes,
    MultiSet,
    SpaceSeparatedList,
    String,
    TooFewDecimals,
    UnallowedCharacter,
    ZeroDenominator,
    check_result,
    parse_descriptor,
)
from skoljka.utils.testcase import SimpleTestCase


class EvaluatorV1Test(SimpleTestCase):
    def assertVariableTypes(self, variable_types, tests):
        for test in tests:
            try:
                result = parse_descriptor(test)
            except:  # noqa: E722
                print("Failed on the test case {}.".format(test))
                raise
            self.assertEqual(
                len(result), len(variable_types), msg="Descriptor: {}".format(test)
            )
            for k in xrange(len(result)):
                self.assertIsInstance(
                    result[k],
                    variable_types[k],
                    msg="test={} k={} expected={} result={}".format(
                        test, k, variable_types[k], result[k]
                    ),
                )

    def assertMultipleVariableTypesOrRaises(self, variable_types, tests):
        for test_case in tests:
            descriptor, exception = test_case
            try:
                if exception is not None:
                    self.assertRaises(exception, parse_descriptor, descriptor)
                    continue

                result = parse_descriptor(descriptor)
                self.assertEqual(
                    len(result),
                    len(variable_types),
                    msg="Descriptor: {}".format(descriptor),
                )
                for k in xrange(len(result)):
                    msg = "descriptor={} k={} expected={} result={}".format(
                        descriptor, k, variable_types[k], result[k]
                    )
                    self.assertIsInstance(result[k], variable_types[k], msg)
            except Exception as e:
                print(
                    "Unexpected exception '{}' ({}) for test case {}.".format(
                        e, type(e), test_case
                    )
                )
                raise

    def assertGetSampleSolution(self, tests):
        """Given a list of `(descriptor, result)` test cases, check if the
        `descriptor` sample solution is equal to `result`.
        """
        for descriptor, result in tests:
            variables = safe_parse_descriptor(evaluator_v1, descriptor)
            sample = get_sample_solution(variables)
            if sample != result:
                print("DESCRIPTOR", descriptor)
                print("VARIABLES", variables)
                print("SAMPLE", sample)
                print("EXPECTED", result)
            self.assertEqual(sample, result)

    def test_validate_descriptor_integer(self):
        self.assertMultipleVariableTypesOrRaises(
            [Integer],
            [
                ("0", None),
                ("000", AmbiguousNumberOrString),
                ("0012", AmbiguousNumberOrString),
            ],
        )

    def test_parse_descriptor(self):
        """Test |-separation and whitespace trim."""
        self.assertEqual(len(parse_descriptor("1 | 2")), 2)
        self.assertEqual(len(parse_descriptor("1 || 2")), 2)
        self.assertEqual(len(parse_descriptor("|||1 ||")), 1)
        self.assertEqual(len(parse_descriptor("|||||")), 0)

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

    def test_sample_solution_integer(self):
        tests = [
            ("0", "0"),
            ("-0", "0"),
            ("123", "123"),
            ("+123", "123"),
            ("-123", "-123"),
        ]
        self.assertGetSampleSolution(tests)

    def test_validate_descriptor_float(self):
        self.assertMultipleVariableTypesOrRaises(
            [Float],
            [
                ("0012.23", AmbiguousNumberOrString),
                ("0012,23", AmbiguousNumberOrString),
                (".23", None),
                (",23", AmbiguousFloatOrList),
                ("23.", None),
                ("23,", AmbiguousFloatOrList),
                ("12.123", None),
                ("12,123", AmbiguousFloatOrList),
            ],
        )

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
            ("-0.00", "0.005", False),
            ("-0.00", "0.004", True),
            ("-0.00", "0.0049999999999999999999", True),
            ("-0.00", "-0.0049999999999999999999", True),
            ("-0.00", "-0.005", False),
            ("-0.00", "0.00", True),
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

    def test_sample_solution_float(self):
        tests = [
            ("0.00", "0.00"),
            ("-0.00", "-0.00"),
            ("123.120000", "123.120000"),
            ("-456.0123", "-456.0123"),
        ]
        self.assertGetSampleSolution(tests)

    def test_validate_descriptor_fraction(self):
        self.assertMultipleVariableTypesOrRaises(
            [Fraction],
            [
                ("0/1", None),
                ("10/5", None),
                ("123/0", ZeroDenominator),
                ("0\\1", None),
                ("10\\5", None),
                ("123\\0", ZeroDenominator),
            ],
        )

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

    def test_sample_solution_fraction(self):
        tests = [
            ("0/1", "0/1"),
            ("5/3", "5/3"),
            ("6/4", "6/4"),
            ("-6/4", "-6/4"),
            ("6/-4", "6/-4"),
            ("-6/-4", "-6/-4"),
            ("6000/7123", "6000/7123"),
        ]
        self.assertGetSampleSolution(tests)

    def test_validate_descriptor_list(self):
        self.assertMultipleVariableTypesOrRaises(
            [List],
            [
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
                ("1/2, 3/1", None),
                ("[123, 12, 232]", None),
                ("[123]", None),
                ("#:123", InvalidModifiers),
                ("#:[123]", InvalidModifiers),
                (u"\u0161", UnallowedCharacter),  # TODO: move to general
            ],
        )

    def test_evaluate_list(self):
        tests = [
            ("1,2,3,4,5", "1, 2, 3, 4, 5", True),
            ("1,2,3,4,5", "1,2, 3,   4, 5", True),
            ("1,2,3,4,5", ",2,3,4,5", InvalidSolution),
            ("1,2,3,4,5", "1,2,,4,5", InvalidSolution),
            ("1,2,3,4,5", "1 2,3,4,5", InvalidSolution),
            ("1,2,3,4,5", "1,2,3,4,5,6", False),
            ("1,2,3,4,5", "1,2,3,4,5,6.5", InvalidSolution),
            ("1,2,3,4,5", "1, 2, 3, 4.5", InvalidSolution),
            ("1,2,3,4,5", "1, 2, 3, 4", False),
            ("1/2, 3/1", "1/2,3", True),
            ("1/2, 3/1", "10/20,6/2", True),
            ("1/2, 3/1", "1,3", False),
            ("#:1,2,3,4,5", "1, 2, 3, 4.5", InvalidSolution),
            ("#:1,2,3,4,5", "1, 2, 3, 4", IncorrectNumberOfElements),
            ("a, b, c, d", "a, b, c, d", True),
            ("a, b, c, d", "d, c, b, a", False),
        ]
        self.assertVariableTypes([List], [x[0] for x in tests])
        self.assertMultipleEqualOrRaise(check_result, tests)

    def test_sample_solution_list(self):
        tests = [
            ("1,2,3,4,5", "1,2,3,4,5"),
            ("1,2  ,3,4, 5", "1,2,3,4,5"),
            ("1.0, 2.0, 3.0, 4.0, 5.0", "1.0,2.0,3.0,4.0,5.0"),
            ("aa,bb,cc,dd", "aa,bb,cc,dd"),
            ("#:aa,bb,cc,dd", "aa,bb,cc,dd"),
            ("1/2,3/4,5/6", "1/2,3/4,5/6"),
        ]
        self.assertGetSampleSolution(tests)

    def test_validate_descriptor_multiset(self):
        self.assertMultipleVariableTypesOrRaises(
            [MultiSet],
            [
                ("{12}", None),
                ("{12,12,12}", None),
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
            ],
        )

    def test_evaluate_multiset(self):
        tests = [
            ("{1,2,3,4,5}", "1, 2, 3, 4, 5", True),
            ("{1,2}", "1,2", True),
            ("{1,2}", "1,1,2", False),
            ("{1,1,1,2}", "1,2", False),
            ("{1,1,1,2}", "1,2,1,1", True),
            ("{2/3, 1/2, 1/2}", "1/2, 2/3, 3/6", True),
            ("{1.0,2.0,3.0,4.5}", "1.001, 2.00, 3.01, 4.500", True),
        ]
        self.assertVariableTypes([MultiSet], [x[0] for x in tests])
        self.assertMultipleEqualOrRaise(check_result, tests)

    def test_sample_solution_multiset(self):
        tests = [
            ("{1,2,3,4,5}", "1,2,3,4,5"),
            ("1,2  ,3,4, 5", "1,2,3,4,5"),
            ("1.0, 2.0, 3.0, 4.0, 5.0", "1.0,2.0,3.0,4.0,5.0"),
            ("aa,bb,cc,dd", "aa,bb,cc,dd"),
            ("1/2,3/4,5/6", "1/2,3/4,5/6"),
        ]
        self.assertGetSampleSolution(tests)

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

    def test_sample_solution_string(self):
        tests = [
            ("00:50", "00:50"),
            ("sarma", "sarma"),
            ("=002", "002"),
        ]
        self.assertGetSampleSolution(tests)

    def test_evaluate_multiple(self):
        from django.utils.translation import deactivate_all

        deactivate_all()  # So that we can test this "OR".

        # Descriptor, solution, is_correct, variable_types.
        tests = [
            ("100 | -100", "100", True, [Integer, Integer]),
            ("100 | -100", "-100", True, [Integer, Integer]),
            ("100 | -100", "200", False, [Integer, Integer]),
            ("100 | -100", "kifla", InvalidSolution, [Integer, Integer]),
            ("100 | sarma", "kifla", False, [Integer, String]),
            ("100 | sarma", "100", True, [Integer, String]),
            ("100 | sarma", "sarma", True, [Integer, String]),
            ("{1,2} | {1}", "1,2", True, [MultiSet, MultiSet]),
            ("{1,2} | {1}", "1", True, [MultiSet, MultiSet]),
            ("{1,2} | {1}", "2", False, [MultiSet, MultiSet]),
            ("sarma|sarma", "sarma", True, [String, String]),
            ("sarma|sarma", "sarma|sarma", False, [String, String]),
            ("sarma\\|sarma", "sarma|sarma", True, [String]),
            ("sarma\\|sarma", "sarma", False, [String]),
            ("sarma\\|sarma", "sarma|sarma", True, [String]),
            ("sarma\\\\|kifla", "kifla", True, [String, String]),
            ("sarma\\\\|kifla", "sarma\\", True, [String, String]),
            ("sarma\\\\|kifla", "sarma", False, [String, String]),
        ]

        for descriptor, solution, is_correct, variable_types in tests:
            self.assertVariableTypes(variable_types, [descriptor])

        _tests = [(a, b, c) for a, b, c, d in tests]
        self.assertMultipleEqualOrRaise(check_result, _tests)

    def test_get_sample_solution_multiple(self):
        from django.utils.translation import deactivate_all

        deactivate_all()  # So that we can test this "OR".
        tests = [
            ("00:50 | sarma | [biftek, kifla]", "00:50 OR sarma OR biftek,kifla"),
            ("100 | 100.00 | -100", "100 OR 100.00 OR -100"),
        ]
        self.assertGetSampleSolution(tests)
