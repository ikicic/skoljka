from django.utils.translation import ugettext as _

from evaluator_base import *

import re

# Here Variable takes care of different solutions, and not the evaluator.
class VariableV0(Variable):
    """Case insensitive solutions, where all whitespace is ignored.

    Different solutions can be split using a vertical bar '|'.
    """
    def __init__(self, descriptor):
        self.descriptor = re.sub(r'\s+', '', descriptor).lower().split('|')

    def evaluate_solution(self, value):
        value = re.sub(r'\s+', '', value).lower()
        return result in self.descriptor

    def help_text(self):
        return ""

    def get_sample_solution(self):
        return self.descriptor[0]

    @staticmethod
    def help_type():
        return ""

    @staticmethod
    def help_for_authors():
        return ""

    @staticmethod
    def help_for_competitors():
        return _("Follow the instructions in the problem description. In the "
                 "case the result is a number, please make sure to use the "
                 "exact number of decimals as required.")


def parse_descriptor(descriptor):
    return [VariableV0(descriptor)]


def check_result(descriptor, result):
    """Checks if the given solution is correct.

    Raises an exception if the format of the solution is invalid.
    Otherwise, returns True if solution is correct, False if incorrect.
    """
    return VariableV0(descriptor).evaluate_solution(result)


def get_variable_types():
    return [VariableV0]


def help_authors_general():
    return _("Split different correct results with a '|' character. "
             "Character '|' cannot be a part of the result. "
             "Trailing and leading spaces are always ignored.")
