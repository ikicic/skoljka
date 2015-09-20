# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _, ungettext

from evaluator_base import InvalidSolution, NotThisFormat, InvalidDescriptor
from evaluator_base import Variable

import re

integer_re = re.compile(r'^[+-]?\d+$')
float_re = re.compile(r'^[-+]?(\d+[,.]\d*|\d*[,.]\d+)$')
fraction_re = re.compile(r'^[-+]?\d+[/\\][-+]?\d+$')
fraction_slash_re = re.compile(r'[/\\]')

ambiguous_number_or_string_re = re.compile(r'^0\d+[,.]?\d*$')
ambiguous_float_or_list_re = re.compile(r'^[+-]?(\d*,\d+|\d+,\d*)$')
space_separated_list_re = re.compile(r'\w \w')  # \w == alphanumeric

# Solution exceptions.
class IncorrectNumberOfElements(InvalidSolution):
    def __init__(self, msg=None):
        if msg is None:
            msg = _("Invalid number of elements!")
        super(IncorrectNumberOfElements, self).__init__(msg)

class TooFewDecimals(InvalidSolution):
    def __init__(self, msg=None):
        if msg is None:
            msg = _("Too few decimals!")
        super(TooFewDecimals, self).__init__(msg)

# Solution descriptor exceptions.
class MixedTypes(InvalidDescriptor):
    def __init__(self, msg=None):
        if msg is None:
            msg = _("Mixed types of elements not allowed!")
        super(InvalidDescriptor, self).__init__(msg)

class MixedPrecisions(InvalidDescriptor):
    def __init__(self, msg=None):
        if msg is None:
            msg = _("Mixed precisions not allowed!")
        super(MixedPrecisions, self).__init__(msg)

class UnallowedCharacter(InvalidDescriptor):
    def __init__(self, msg=None):
        if msg is None:
            msg = _("Unallowed characters!")
        super(UnallowedCharacter, self).__init__(msg)

class InvalidModifiers(InvalidDescriptor):
    def __init__(self, msg=None):
        if msg is None:
            msg = _("Invalid modifiers!")
        super(InvalidDescriptor, self).__init__(msg)

class AmbiguousNumberOrString(InvalidDescriptor):
    def __init__(self, msg=None):
        if msg is None:
            msg = _("Ambiguous, is it a number or a string?")
        super(AmbiguousNumberOrString, self).__init__(msg)

class AmbiguousFloatOrList(InvalidDescriptor):
    def __init__(self, msg=None):
        if msg is None:
            msg = _("Ambiguous, is it a float or a list?")
        super(AmbiguousFloatOrList, self).__init__(msg)

class SpaceSeparatedList(InvalidDescriptor):
    def __init__(self, msg=None):
        if msg is None:
            msg = _("Elements must be separated by a comma!")
        super(SpaceSeparatedList, self).__init__(msg)

class ZeroDenominator(InvalidDescriptor):
    def __init__(self, msg=None):
        if msg is None:
            msg = _("Denominator cannot be 0!")
        super(ZeroDenominator, self).__init__(msg)


# Variables
class Integer(Variable):
    def __init__(self, descriptor):
        super(Integer, self).__init__(descriptor)
        try:
            self.value = int(descriptor)
        except ValueError:
            raise NotThisFormat

    def evaluate_solution(self, value):
        if not integer_re.match(value):
            raise InvalidSolution

        return self.value == int(value)

    def help_text(self):
        return ""

    @staticmethod
    def help_type():
        return _("Integer")

    @staticmethod
    def help_for_authors():
        return ""  # No help needed.

    @staticmethod
    def help_for_competitors():
        return ""  # No help needed.


class Float(Variable):
    def __init__(self, descriptor):
        super(Float, self).__init__(descriptor)
        if not float_re.match(descriptor):
            raise NotThisFormat
        self.sign = -1 if descriptor[0] == '-' else 1
        if descriptor[0] in '-+':
            descriptor = descriptor[1:]
        self.integer, self.fractional = re.split('[.,]', descriptor)
        self.decimal_count = len(self.fractional)

    def evaluate_solution(self, value):
        if not float_re.match(value):
            if integer_re.match(value):
                raise TooFewDecimals
            raise InvalidSolution
        sign = -1 if value[0] == '-' else 1
        if value[0] in '-+':
            value = value[1:]
        integer, fractional = re.split('[.,]', value)
        if len(fractional) < len(self.fractional):
            raise TooFewDecimals
        if len(self.fractional) == len(fractional):
            return self.sign * int(self.integer + self.fractional) == \
                   sign * int(integer + fractional)
        extra = len(fractional) - len(self.fractional)
        margin = 5 * 10 ** (extra - 1)
        descriptor = int(self.integer + self.fractional + '0' * extra)
        given = int(integer + fractional)
        given *= sign * self.sign
        if descriptor == 0:
            return -margin < given and given < margin
        return descriptor - margin <= given and given < descriptor + margin

    def help_text(self):
        return ungettext(
                "Write the result rounded to %(count)d decimal.",
                "Write the result rounded to %(count)d decimals.",
                self.decimal_count) % {'count': self.decimal_count}

    @staticmethod
    def help_type():
        return _("Decimal number")

    @staticmethod
    def help_for_authors():
        return _("The solution is required to have at least as many decimals "
                 "as entered by the author, otherwise it will be rejected. The "
                 "solution is accepted if and only if it is equal to the "
                 "author's solution when rounded to the same number of "
                 "decimals. If you are unsure about how the rounding is "
                 "performed, please try sending the solution with more "
                 "decimals than required. Please prefer dots over commas as a "
                 "decimal mark.")

    @staticmethod
    def help_for_competitors():
        return _("The solution must have as least as many decimals as written "
                 "in the description, and has to exactly match the official "
                 "solution when rounded to that number of decimals.")


class Fraction(Variable):
    def __init__(self, descriptor):
        super(Fraction, self).__init__(descriptor)
        if not fraction_re.match(descriptor):
            raise NotThisFormat
        a, b = fraction_slash_re.split(descriptor)
        self.num = int(a)
        self.den = int(b)
        if self.den == 0:
            raise ZeroDenominator

    def evaluate_solution(self, value):
        try:
            fraction = Fraction(value)
        except ZeroDenominator:
            raise InvalidSolution
        except NotThisFormat:
            try:
                c = int(value)
            except ValueError:
                raise InvalidSolution
            return c * self.den == self.num
        return fraction.num * self.den == fraction.den * self.num

    def help_text(self):
        return _("Write the solution in the form a/b, where a and b are "
                 "integers.")

    @staticmethod
    def help_type():
        return _("Fraction")

    @staticmethod
    def help_for_authors():
        return _("Fraction is written in the format a/b, where a and b are "
                 "integers. The competitors solution will be accepted if it is "
                 "an integer or a fraction equal to the given fraction. "
                 "Reducible fractions are also accepted.")

    @staticmethod
    def help_for_competitors():
        return _("Fractions are written in the format a/b, where a and b are "
                 "integers. Reducible fractions are accepted. You can also "
                 "write a single integer if you are sure the result is an "
                 "integer. Decimal numbers are not accepted.")


def _parse_element(part):
    part = part.strip()
    try:
        return Integer(part)
    except NotThisFormat:
        try:
            return Float(part)
        except NotThisFormat:
            try:
                return Fraction(part)
            except NotThisFormat:
                return String(part)


class BaseList(Variable):
    def __init__(self, descriptor):
        super(BaseList, self).__init__(descriptor)
        self.length_specified = descriptor.startswith('#:')
        if self.length_specified:
            descriptor = descriptor[2:]
        self.items = [_parse_element(x) for x in descriptor.split(',')]

        contained = set()
        for var_type in [Integer, Float, Fraction, String]:
            if any(isinstance(x, var_type) for x in self.items):
                contained.add(var_type)
        if len(contained) > 1:
            raise MixedTypes
        if Float in contained:
            for item in self.items:
                if item.decimal_count != self.items[0].decimal_count:
                    raise MixedPrecisions
        self.element_type = list(contained)[0]


class List(BaseList):
    def __init__(self, descriptor):
        brackets = False
        if descriptor[-1] == ']':
            if descriptor[0] == '[':
                brackets = True
                super(List, self).__init__(descriptor[1:-1])
            elif descriptor.startswith('#:') and descriptor[2] == '[':
                brackets = True
                super(List, self).__init__('#:' + descriptor[3:-1])
            else:
                super(List, self).__init__(descriptor)
        else:
            super(List, self).__init__(descriptor)

        if len(self.items) == 1:
            if self.length_specified:
                raise InvalidModifiers
            if not brackets:
                raise NotThisFormat


    def evaluate_solution(self, value):
        items = [item.strip() for item in value.split(',')]
        if self.length_specified and len(self.items) != len(items):
            raise IncorrectNumberOfElements

        is_correct = len(self.items) == len(items)
        for k in xrange(len(items)):
            # Only one type and one Float precision currently supported.
            # If the number of items not matching, call to check format.
            index = k if k < len(self.items) else 0
            if not self.items[k].evaluate_solution(items[k]):
                is_correct = False

        return is_correct

    def help_text(self):
        if self.element_type == Integer:
            msg = _("Write the results in the correct order, separated with "
                    "a comma.")
        if self.element_type == Float:
            decimal_count = self.items[0].decimal_count
            msg = ungettext(
                    "Write the results in the correct order, round to "
                    "%(decimals)d decimal and separated with a comma.",
                    "Write the results in the correct order, round to "
                    "%(decimals)d decimals and separated with a comma.",
                    decimal_count) % {'decimals': decimal_count}
        if self.element_type == Fraction:
            msg = _("Write the results in the correct order in the form a/b, "
                    "where a and b are integers. Separate the results with a "
                    "comma.")
        if self.element_type == String:
            msg = _("Write the results in the correct order, separated with a "
                    "comma.")
        if self.length_specified:
            msg += " " + _("Number of elements:") + " " + str(len(self.items))
        return msg

    @staticmethod
    def help_type():
        return _("List")

    @staticmethod
    def help_for_authors():
        return _("A list can contain integers, decimal numbers, fractions or "
                 "strings (anything else). All elements must have the same "
                 "type. Elements are separated with a comma. By default, "
                 "competitors don't know the length of the list. To make the "
                 "length visible, use #: prefix. To make a single-element "
                 "list, put the element into [ ] brackets.")

    @staticmethod
    def help_for_competitors():
        return _("A list can contain integers, decimal numbers, fractions or "
                 "strings (anything else). If not obvious, the type of "
                 "elements will be specified, together with the decimal count "
                 "in the case of decimal numbers. The length of the list might "
                 "or might not be specified. The list can also contain a "
                 "single element! Separate the elements with a comma.")



class MultiSet(BaseList):
    def __init__(self, descriptor):
        if descriptor.startswith('#:'):
            if descriptor[2] == '{' and descriptor[-1] == '}':
                super(MultiSet, self).__init__('#:' + descriptor[3:-1])
                if len(self.items) == 1:
                    raise InvalidModifiers
            else:
                raise NotThisFormat
        elif descriptor[0] == '{' and descriptor[-1] == '}':
            super(MultiSet, self).__init__(descriptor[1:-1])
        else:
            raise NotThisFormat

    def evaluate_solution(self, value):
        items = [item.strip() for item in value.split(',')]
        if self.length_specified and len(self.items) != len(items):
            raise IncorrectNumberOfElements

        # First check if the format of the user's solution is valid.
        # Only one type and one Float precision currently supported.
        for item in items:
            self.items[0].evaluate_solution(item)

        if len(self.items) != len(items):
            return False
        # Sorting solutions might be a really difficult job. That's why we just
        # do the matching of user's solutions with the official in O(N * M).
        available = range(len(self.items))
        for item in items:
            matched = None
            for k in available:
                if self.items[k].evaluate_solution(item):
                    matched = k
                    break
            if matched is None:
                return False
            available.remove(matched)
        return True

    def help_text(self):
        if self.element_type == Integer:
            msg = _("Write the results in any order, separated with a comma.")
        if self.element_type == Float:
            decimal_count = self.items[0].decimal_count
            msg = ungettext(
                    "Write the results in any order, round to "
                    "%(decimals)d decimal and separated with a comma.",
                    "Write the results in any order, round to "
                    "%(decimals)d decimals and separated with a comma.",
                    decimal_count) % {'decimals': decimal_count}
        if self.element_type == Fraction:
            msg = _("Write the results in any order, in the form a/b, "
                    "where a and b are integers. Separate the results with a "
                    "comma.")
        if self.element_type == String:
            msg = _("Write the results in any order, separated with a comma.")
        if self.length_specified:
            msg += " " + _("Number of elements:") + " " + str(len(self.items))
        return msg

    @staticmethod
    def help_type():
        return _("Set")

    @staticmethod
    def help_for_authors():
        return _("Acts similarly to lists, only the elements are treated as "
                 "unordered. Put the comma separated values inside the { } "
                 "brackets. Same as for lists, use #: prefix to make the "
                 "length visible. Warning: Sets behave actually as multisets, "
                 "please write a note in the problem description directly if "
                 "you do except multiple equal values.")

    @staticmethod
    def help_for_competitors():
        return _("Same as for lists, just the order does not matter.")



class String(Variable):
    def __init__(self, descriptor):
        self.value = descriptor

    def evaluate_solution(self, value):
        return self.value == value

    def help_text(self):
        return ""

    @staticmethod
    def help_type():
        return _("String")

    @staticmethod
    def help_for_authors():
        return _("Anything that does not match any other type. To force the "
                 "type to be a string, use = prefix.")

    @staticmethod
    def help_for_competitors():
        return _("Anything that does not match any other type. That can "
                 "include words, special formats, or even numbers of special "
                 "forms.")



def parse_variable(descriptor):
    descriptor = descriptor.strip()
    try:
        str(descriptor)
    except UnicodeEncodeError:
        raise UnallowedCharacter

    if descriptor.startswith('='):
        return String(descriptor[1:])
    else:
        if ambiguous_number_or_string_re.match(descriptor):
            raise AmbiguousNumberOrString
        if ambiguous_float_or_list_re.match(descriptor):
            raise AmbiguousFloatOrList
        if space_separated_list_re.search(descriptor):
            raise SpaceSeparatedList

        try:
            return Integer(descriptor)
        except NotThisFormat:
            pass

        try:
            return Float(descriptor)
        except NotThisFormat:
            pass

        try:
            return Fraction(descriptor)
        except NotThisFormat:
            pass

        try:
            return MultiSet(descriptor)
        except NotThisFormat:
            pass

        try:
            return List(descriptor)
        except NotThisFormat:
            pass

        return String(descriptor)


def parse_descriptor(descriptor):
    """Parse full solution descriptor for v1 evaluator.

    Splits the string by | delimiter and parses each part separately.
    Returns the list of variables, one for each part."""
    variables = []
    descriptor += " |"
    part = ""
    k = 0
    while k < len(descriptor):
        current = descriptor[k]
        if current == '\\' and k < len(descriptor) - 1:
            next_char = descriptor[k + 1]
            if next_char in '\\|':
                part += next_char
                k += 2
                continue
        elif current == '|':
            variables.append(parse_variable(part))
            part = ""
            k += 1
            continue
        part += current
        k += 1
    return variables


def check_result(descriptor, result):
    """Implementation of check_result for v1 evaluator."""
    variables = parse_descriptor(descriptor)
    exception = False
    for variable in variables:
        try:
            if variable.evaluate_solution(result):
                return True
        except InvalidSolution:
            exception = True
    if exception:
        raise
    return False

def get_variable_types():
    return [Integer, Float, Fraction, List, MultiSet, String]

def help_authors_general():
    return _("Split different accepted solutions by a '|' character. "
             "To use the '|' character, write '\\|'. To use '\\', write "
             "'\\\\'. Trailing and leading spaces are always ignored.")
