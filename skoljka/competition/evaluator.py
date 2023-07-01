from django.utils.translation import ugettext as _

import skoljka.competition.evaluator_v0 as evaluator_v0
import skoljka.competition.evaluator_v1 as evaluator_v1
from skoljka.competition.evaluator_base import *

EVALUATOR_V0 = 0
EVALUATOR_V1 = 1


def get_evaluator(evaluator_version):
    if evaluator_version == EVALUATOR_V0:
        return evaluator_v0
    if evaluator_version == EVALUATOR_V1:
        return evaluator_v1
    raise Exception("Unknown evaluator version!")


def safe_parse_descriptor(evaluator, descriptor):
    """Tries to parse the descriptor. If fails, returns the exception."""
    try:
        return evaluator.parse_descriptor(descriptor)
    except InvalidDescriptor as e:
        return e


# Default Evaluator method. Internal.
def get_solution_help_text(variables, error_message="", show_types=False):
    """Generates help text for the given solution descriptor variables.

    Works in pair with safe_parse_descriptor, i.e. if parsing failed, expects
    variables to be an Exception instance."""
    if isinstance(variables, Exception):
        return error_message
    if not variables:
        return ""

    help_type = u""
    help_texts = []
    for var in variables:
        if show_types:
            help_type = u'<span class="chelp-type">{}</span> '.format(var.help_type())
        help_text = var.help_text()
        if help_text:
            help_text = u'<span class="chelp-text">{}</span>'.format(help_text)
        help_texts.append(help_type + help_text)
    help_texts = [text for text in help_texts if text]
    help_texts = list(set(help_texts))
    delimiter = u" " + _(u"OR") + u" "
    return mark_safe(delimiter.join(help_texts))


def get_sample_solution(variables):
    """Concatenate all .get_sample_solutions() of the given variables.

    Catches all exceptions from .get_sample_solutions().
    Compatible with safe_parse_descriptor."""
    if isinstance(variables, Exception):
        return _("Error!")
    try:
        samples = [var.get_sample_solution() for var in variables]
    except:
        return _("Error!")
    delimiter = u" " + _(u"OR") + u" "
    return delimiter.join(samples)
