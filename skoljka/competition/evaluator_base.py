# -*- coding: utf-8 -*-

from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

class InvalidSolution(Exception):
    def __init__(self, msg=None):
        if msg is None:
            msg = _("Invalid solution!")
        super(InvalidSolution, self).__init__(msg)

class NotThisFormat(Exception):
    pass

class InvalidDescriptor(Exception):
    def __init__(self, msg=None):
        if msg is None:
            msg = _("Invalid solution descriptor!")
        super(InvalidDescriptor, self).__init__(msg)

class Variable(object):
    def __init__(self, descriptor):
        """Parse given solution descriptor.

        Throws a NotThisFormat exception if the given solution descriptor does
        not match this format. If the format matches, but there are some
        errors, throws InvalidDescriptor exception. Otherwise, saves any data
        necessary data to correctly evaluate users' solutions."""
        pass

    def evaluate_solution(self, value):
        """Evaluate user's solution.

        Throws a InvalidSolution exception if the given value doesn't have the
        expected format. Otherwise, returns True or False, depending on if the
        solution is correct or not."""
        raise NotImplementedError

    def help_text(self):
        """Returns a string describing the solution format to the user."""
        raise NotImplementedError

    def get_sample_solution(self):
        """Returns a string representing a sample correct solution."""
        raise NotImplementedError

    @staticmethod
    def help_type():
        """Name of the variable type."""
        raise NotImplementedError

    @staticmethod
    def help_for_authors():
        """Description of the format of the solution descriptor."""
        raise NotImplementedError

    @staticmethod
    def help_for_competitors():
        """Help shown to the competitors in the competition rules."""
        raise NotImplementedError
