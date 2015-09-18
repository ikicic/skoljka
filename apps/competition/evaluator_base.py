# -*- coding: utf-8 -*-

class InvalidSolution(Exception):
    def __init__(self, msg="Nevaljano rješenje"):
        super(InvalidSolution, self).__init__(msg)

class NotThisFormat(Exception):
    pass

class InvalidOfficial(Exception):
    def __init__(self, msg="Nevaljan opis rješenja!"):
        super(InvalidOfficial, self).__init__(msg)

class Variable(object):
    def __init__(self, official):
        """Parse given official solution.

        Throws a NotThisFormat exception if the given official solution does
        not match this format. If the format matches, but there are some
        errors, throws InvalidOfficial exception. Otherwise, saves any data
        necessary data to correctly evaluate users' solutions."""
        pass

    def evaluate_solution(self, value):
        """Evaluate user's solution.

        Throws a InvalidSolution exception if the given value doesn't have the
        expected format. Otherwise, returns True or False, depending on if the
        solution is correct or not."""
        raise NotImplementedError
