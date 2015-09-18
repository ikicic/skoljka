# -*- coding: utf-8 -*-

from evaluator_base import InvalidSolution, NotThisFormat, InvalidOfficial
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
    def __init__(self, msg="Nevaljan broj elemanata!"):
        super(IncorrectNumberOfElements, self).__init__(msg)

class TooFewDecimals(InvalidSolution):
    def __init__(self, msg="Premalen broj decimala!"):
        super(TooFewDecimals, self).__init__(msg)

# Official solution exceptions.
class MixedTypes(InvalidOfficial):
    def __init__(self, msg="Miješani tipovi elemenata nisu podržani!"):
        super(InvalidOfficial, self).__init__(msg)

class MixedPrecisions(InvalidOfficial):
    def __init__(self,
                 msg="Miješane preciznosti decimalnih brojeva nisu podržane!"):
        super(MixedPrecisions, self).__init__(msg)

class UnallowedCharacter(InvalidOfficial):
    def __init__(self, msg="Nedozvoljeni znakovi!"):
        super(UnallowedCharacter, self).__init__(msg)

class InvalidModifiers(InvalidOfficial):
    def __init__(self, msg="Nevaljani modifikatori!"):
        super(InvalidOfficial, self).__init__(msg)

class AmbiguousNumberOrString(InvalidOfficial):
    def __init__(self, msg="Dvosmisleno, broj ili string?"):
        super(AmbiguousNumberOrString, self).__init__(msg)

class AmbiguousFloatOrList(InvalidOfficial):
    def __init__(self, msg="Dvosmisleno, decimalni broj ili lista?"):
        super(AmbiguousFloatOrList, self).__init__(msg)

class SpaceSeparatedList(InvalidOfficial):
    def __init__(self, msg="Elementi moraju biti odvojeni zarezom!"):
        super(SpaceSeparatedList, self).__init__(msg)

class ZeroDenominator(InvalidOfficial):
    def __init__(self, msg="Nazivnik ne može biti nula!"):
        super(ZeroDenominator, self).__init__(msg)


# Variables
class Integer(Variable):
    def __init__(self, official):
        super(Integer, self).__init__(official)
        try:
            self.value = int(official)
        except ValueError:
            raise NotThisFormat

    def evaluate_solution(self, value):
        if not integer_re.match(value):
            raise InvalidSolution

        return self.value == int(value)


class Float(Variable):
    def __init__(self, official):
        super(Float, self).__init__(official)
        if not float_re.match(official):
            raise NotThisFormat
        self.sign = -1 if official[0] == '-' else 1
        if official[0] in '-+':
            official = official[1:]
        self.integer, self.fractional = re.split('[.,]', official)

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
        official = int(self.integer + self.fractional + '0' * extra)
        given = int(integer + fractional)
        given *= sign * self.sign
        if official == 0:
            return -margin < given and given < margin
        return official - margin <= given and given < official + margin

    def get_decimal_count(self):
        return len(self.fractional)


class Fraction(Variable):
    def __init__(self, official):
        super(Fraction, self).__init__(official)
        if not fraction_re.match(official):
            raise NotThisFormat
        a, b = fraction_slash_re.split(official)
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
    def __init__(self, official):
        super(BaseList, self).__init__(official)
        self.length_specified = official.startswith('#:')
        if self.length_specified:
            official = official[2:]
        self.items = [_parse_element(x) for x in official.split(',')]

        contained = set()
        for var_type in [Integer, Float, Fraction, String]:
            if any(isinstance(x, var_type) for x in self.items):
                contained.add(var_type)
        if len(contained) > 1:
            raise MixedTypes
        if Float in contained:
            for item in self.items:
                if item.get_decimal_count() != \
                        self.items[0].get_decimal_count():
                    raise MixedPrecisions


class List(BaseList):
    def __init__(self, official):
        brackets = False
        if official[-1] == ']':
            if official[0] == '[':
                brackets = True
                super(List, self).__init__(official[1:-1])
            elif official.startswith('#:') and official[2] == '[':
                brackets = True
                super(List, self).__init__('#:' + official[3:-1])
            else:
                super(List, self).__init__(official)
        else:
            super(List, self).__init__(official)

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


class MultiSet(BaseList):
    def __init__(self, official):
        if official.startswith('#:'):
            if official[2] == '{' and official[-1] == '}':
                super(MultiSet, self).__init__('#:' + official[3:-1])
                if len(self.items) == 1:
                    raise InvalidModifiers
            else:
                raise NotThisFormat
        elif official[0] == '{' and official[-1] == '}':
            super(MultiSet, self).__init__(official[1:-1])
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


class String(Variable):
    def __init__(self, official):
        self.value = official

    def evaluate_solution(self, value):
        return self.value == value


def parse_variable(official):
    official = official.strip()
    try:
        str(official)
    except UnicodeEncodeError:
        raise UnallowedCharacter

    if official.startswith('='):
        return String(official[1:])
    else:
        if ambiguous_number_or_string_re.match(official):
            raise AmbiguousNumberOrString
        if ambiguous_float_or_list_re.match(official):
            raise AmbiguousFloatOrList
        if space_separated_list_re.search(official):
            raise SpaceSeparatedList

        try:
            return Integer(official)
        except NotThisFormat:
            pass

        try:
            return Float(official)
        except NotThisFormat:
            pass

        try:
            return Fraction(official)
        except NotThisFormat:
            pass

        try:
            return MultiSet(official)
        except NotThisFormat:
            pass

        try:
            return List(official)
        except NotThisFormat:
            pass

        return String(official)


def parse_official(official):
    """Parse full official solution for v1 evaluator.

    Splits the string by | delimiter and parses each part separately.
    Returns the list of variables, one for each part."""
    variables = []
    official += " |"
    part = ""
    k = 0
    while k < len(official):
        current = official[k]
        if current == '\\' and k < len(official) - 1:
            next_char = official[k + 1]
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


def check_result(correct_result, result):
    """Implementation of check_result for v1 evaluator."""
    variables = parse_official(correct_result)
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
