# -*- coding: utf-8 -*-

# Okay to import everything, as evaluator_base is just a way to solve import
# cycles.
from evaluator_base import *
import evaluator_v1

EVALUATOR_V0 = 0
EVALUATOR_V1 = 1

class VariableV0(Variable):
    def __init__(self, official):
        self.correct_results = re.sub(r'\s+', '', official).lower().split('|')

    def evaluate_solution(self, value):
        value = re.sub(r'\s+', '', value).lower()
        return result in self.correct_results

class EvaluatorV0(object):
    def parse_official(self, official):
        return VariableV0(official)

    def check_result(self, correct_result, result):
        """Implementation of check_result for v0 evaluator."""
        return VariableV0(correct_result).evaluate_solution(result)
evaluator_v0 = EvaluatorV0()


def parse_official(evaluator_version, official):
    if evaluator_version == EVALUATOR_V0:
        return evaluator_v0.parse_official(official)
    if evaluator_version == EVALUATOR_V1:
        return evaluator_v1.parse_official(official)
    raise Exception("Unknown evaluator version")


def check_result(evaluator_version, correct_result, result):
    """Checks if the given solution is correct.

    Raises an exception if the format of the solution is invalid.
    Otherwise, returns True if solution is correct, False if incorrect.
    """
    if evaluator_version == EVALUATOR_V0:
        return evaluator_v0.check_result(correct_result, result)
    if evaluator_version == EVALUATOR_V1:
        return evaluator_v1.check_result(correct_result, result)
    raise Exception("Unknown evaluator version")
