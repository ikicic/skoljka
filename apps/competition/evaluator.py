from django.utils.translation import ugettext as _
from evaluator_base import *
import evaluator_v0
import evaluator_v1

EVALUATOR_V0 = 0
EVALUATOR_V1 = 1

def get_evaluator(evaluator_version):
    if evaluator_version == EVALUATOR_V0:
        return evaluator_v0
    if evaluator_version == EVALUATOR_V1:
        return evaluator_v1
    raise Exception("Unknown evaluator version!")


# Default Evaluator method. Internal.
def get_solution_help_text(evaluator, descriptor, error_message="",
        show_types=False):
    """Generates help text for the given solution descriptor."""
    if not descriptor:
        return ""
    try:
        variables = evaluator.parse_descriptor(descriptor)
    except InvalidDescriptor:
        return error_message

    help_type = u""
    help_texts = []
    for var in variables:
        if show_types:
            help_type = u'<span class="chelp-type">{}</span> '.format(
                    var.help_type())
        help_text = var.help_text()
        if help_text:
            help_text = u'<span class="chelp-text">{}</span>'.format(help_text)
        help_texts.append(help_type + help_text)
    help_texts = [text for text in help_texts if text]
    help_texts = list(set(help_texts))
    delimiter = u" " + _(u"OR") + u" "
    return mark_safe(delimiter.join(help_texts))
