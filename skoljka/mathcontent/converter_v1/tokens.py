from django.utils.translation import ugettext as _

from skoljka.mathcontent.converter_v1.basics import SKIP_COMPARISON, test_eq

# Unprocesssed tokens.
TOKEN_COMMAND = 20
TOKEN_OPEN_CURLY = 30
TOKEN_CLOSED_CURLY = 31
TOKEN_OPEN_SQUARE = 32
TOKEN_CLOSED_SQUARE = 33

# Processed tokens.
class Token(object):
    def __eq__(self, other):
        return test_eq(self, other)

class TokenComment(Token):
    def __init__(self, text):
        self.text = text
    def __repr__(self):
        return 'TokenComment({})'.format(repr(self.text))

class TokenMath(Token):
    def __init__(self, format, content, force_inline=False):
        self.format = format
        self.content = content
        self.force_inline = force_inline
    def __repr__(self):
        return 'TokenMath({}, {}, {})'.format(
                repr(self.format), repr(self.content), repr(self.force_inline))

class TokenText(Token):
    def __init__(self, text):
        self.text = text
    def __repr__(self):
        return 'TokenText({})'.format(repr(self.text))

class TokenMultilineWhitespace(Token):
    """Paragraph-breaking whitespace, contains at least two line breaks."""
    def __init__(self, text):
        self.text = text
    def __repr__(self):
        return 'TokenMultilineWhitespace({})'.format(repr(self.text))

class TokenSimpleWhitespace(Token):
    """Paragraph-non-breaking whitespace, contains at most one line break."""
    def __init__(self, text):
        self.text = text
    def __repr__(self):
        return 'TokenSimpleWhitespace({})'.format(repr(self.text))

class TokenError(Token):
    def __init__(self, error_message, content):
        self.error_message = error_message
        self.content = content
    def __repr__(self):
        return 'TokenError({}, {})'.format(
                repr(self.error_message), repr(self.content))

class TokenWarning(TokenError):
    def __init__(self, error_message, content):
        if error_message != SKIP_COMPARISON:
            self.error_message = _("Warning:") + " " + error_message
        self.error_message = error_message
        self.content = content
    def __repr__(self):
        return 'TokenWarning({}, {})'.format(
                repr(self.error_message), repr(self.content))

class TokenCommand(Token):
    def __init__(self, command, part=0, args=[], whitespace=SKIP_COMPARISON):
        self.command = command
        self.args = args
        self.part = part
        # SKIP_COMPARISON used only for testing, the real code MUST manually
        # set whitespace.
        self.whitespace = whitespace
    def __repr__(self):
        return 'TokenCommand({}, part={}, args={}, whitespace={})'.format(
                repr(self.command), self.part, repr(self.args),
                repr(self.whitespace))

class TokenOpenCurly(Token):
    def __repr__(self):
        return 'TokenOpenCurly()'

class TokenClosedCurly(Token):
    def __repr__(self):
        return 'TokenClosedCurly()'

class TokenBBCode(Token):
    def __init__(self, name, attrs, T_start, T_end, content=None):
        self.name = name
        self.attrs = attrs      # None if closed tag.
        self.T_start = T_start  # Original interval of the input string.
        self.T_end = T_end
        self.content = content  # Only if the content not parsed.

    def __repr__(self):
        return 'TokenBBCode({}, {}, {}, {})'.format(
                repr(self.name), repr(self.attrs), self.T_start, self.T_end)
    def is_open(self):
        return self.attrs is not None


