from django.utils.translation import ugettext as _

from mathcontent.models import TYPE_HTML, TYPE_LATEX

COUNTER_EQUATION = 1
COUNTER_FIGURE = 2


class State(object):
    def __init__(self, break_condition=None, environment=None):
        self.tokens = []
        self.break_condition = break_condition
        self.environment = environment  # LatexEnvironment instance.

    def add_token(self, tokens):
        self.tokens.append(tokens)  # Flatten later.



class ParseError(Exception):
    pass



def float_to_str_pretty(val):
    return "{}".format(val).rstrip('0').rstrip('.')


def img_parse_length(value):
    try:
        return int(value)
    except:
        pass
    if value[-2:] in ['px', 'pt']:
        try:
            return int(value[:-2])
        except:
            pass
    raise ParseError(_("Unexpected value:") + " " + value)


def img_params_to_html(params):
    width = None
    height = None
    for name, value in params:
        name = name.lower()
        if name == 'width':
            width = img_parse_length(value)
        elif name == 'height':
            height = img_parse_length(value)
        elif name == 'scale':
            try:
                scale = float(value)
            except:
                raise ParseError(_("Unexpected value:") + " " + value)
            width = float_to_str_pretty(100 * scale) + "%"
            height = float_to_str_pretty(100 * scale) + "%"
        elif name != 'attachment' and name != 'img':
            raise ParseError(_("Unexpected attribute:") + " " + name)
    return (' width="{}"'.format(width) if width else '') + \
           (' height="{}"'.format(height) if height else '')

########################################################
# Test utils
########################################################
# Use in unit tests to skip a comparison of a certain field.
class _SkipComparison():
    def __repr__(self):
        return '<<SKIP>>'

SKIP_COMPARISON = _SkipComparison()
def test_eq(A, B):
    """Compare two objects. Skip comparison of keys with a value
    SKIP_COMPARISON (it is still required that both objects have the same keys).
    """
    if A.__class__ != B.__class__:
        return False
    x = A.__dict__
    y = B.__dict__
    if x == y:
        return True
    for key, value in x.iteritems():
        if key not in y:
            return False
        if value != y[key] and value != SKIP_COMPARISON and \
                y[key] != SKIP_COMPARISON:
            return False
    # It suffices to compare only if they have the same keys.
    return x.keys() == y.keys()
