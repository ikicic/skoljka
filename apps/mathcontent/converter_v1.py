from django.utils.translation import ugettext as _

from skoljka.libs import flatten_ignore_none, xss
from skoljka.libs.string_operations import startswith_ex

from mathcontent.models import ERROR_DEPTH_VALUE, IMG_URL_PATH, TYPE_HTML, \
        TYPE_LATEX
from mathcontent.latex import generate_png, generate_latex_hash, \
        get_available_latex_elements

from collections import defaultdict
from urlparse import urljoin

import copy
import re

# TODO: Paragraphs!
# TODO: Support for starred commands.
#  E.g. \\* which does nothing in HTML.
# TODO: \\[5pt]
# TODO: \newline
# TODO: \par
# TODO: Quotation marks ``text'' and `text' for HTML.
# TODO: -, -- (en-dash), --- (em-dash) and other ligatures
# TODO: Fig.~5  (treat as a LaTeX-only feature)
# TODO: \begin{enumerate} \item ... \end{enumerate}
# TODO: \begin{itemize} \item ... \end{itemize}
# TODO: \begin{description} \item[bla] ... \end{description}
# TODO: Support recursive enumerate / itemize / description.
# TODO: \begin{quote}...\end{quote}
# TODO: \begin{multline}...\end{multline}
# TODO: \begin{eqnarray}...\end{eqnarray}
# TODO: fix uline and sout --> support for custom usepackage

# MAYBE: \" \i \j \o \^ \ss \~ and other special characters
# MAYBE: \begin{verbatim}...\end{verbatim}
# MAYBE: \verb+asdf+
# MAYBE: \begin{verbatim*} and \verb*
# MAYBE: \newpage
# MAYBE: \(no)linebreak[n]
# MAYBE: \(no)pagebreak[n]
# MAYBE: \begin{comment}...\end{comment} with \usepackage{verbatim}


COUNTER_EQUATION = 1
COUNTER_FIGURE = 2

ROOT_BLOCK_NAME = 'root'

RE_ASCII_ALPHA_SINGLE_CHAR = re.compile('[a-zA-Z]')
_NT__READ_TEXT__END_CHAR = set('{}[]$\n\r\\%')

escape_table = {
    # NOT TESTED.
    TYPE_HTML: {
        '&': '&amp;',
        '"': '&quot;',
        "'": '&apos;',
        '>': '&gt;',
        '<': '&lt;',
    },
    # NOT TESTED.
    TYPE_LATEX: {
        '#': '\\#',
        # '%': '\\%',
        '^': '\\textasciicircum{}',
        '&': '\\&',
        '_': '\\_',
        '{': '\\{',
        '}': '\\}',
        '~': '\\~{}',
        '\\': '\\textbackslash{}',
    },
}

########################################################
# Test utils
########################################################
# Use in unit tests to skip a comparison of a certain field.
class _SkipComparison():
    def __repr__(self):
        return '<<SKIP>>'

SKIP_COMPARISON = _SkipComparison()
def _test_eq(A, B):
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


########################################################
# Tokens
########################################################
# Unprocesssed tokens.
TOKEN_COMMAND = 20
TOKEN_OPEN_CURLY = 30
TOKEN_CLOSED_CURLY = 31
TOKEN_OPEN_SQUARE = 32
TOKEN_CLOSED_SQUARE = 33


# Processed tokens.
class Token(object):
    def __eq__(self, other):
        return _test_eq(self, other)

class TokenComment(Token):
    def __init__(self, text):
        self.text = text
    def __repr__(self):
        return 'TokenComment({})'.format(repr(self.text))

class TokenMath(Token):
    def __init__(self, format, content):
        self.format = format
        self.content = content
    def __repr__(self):
        return 'TokenMath({}, {})'.format(repr(self.format), repr(self.content))

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
        self.attrs = attrs
        self.T_start = T_start  # Original interval of the input string.
        self.T_end = T_end
        self.content = content
    def __repr__(self):
        return 'TokenBBCode({}, {}, {}, {})'.format(
                repr(self.name), repr(self.attrs), self.T_start, self.T_end)
    def is_open(self):
        return self.attrs is not None


########################################################
# Exceptions
########################################################
# TODO: Handle exceptions.
class BBCodeException(Exception):
    pass


class ParseError(Exception):
    pass

class LatexValueError(Exception):
    pass

class CriticalError(ParseError):
    def __init__(self, converter, index, msg):
        self.converter = converter
        self.index = index
        super(CriticalError, self).__init__(msg)


class LatexSyntaxError(ParseError):
    pass

class UnknownEnvironment(ParseError):
    pass

class TooManyParseErrors(ParseError):
    pass

class ParserInternalError(Exception):
    pass


########################################################
# General helper functions.
########################################################
def float_to_str_pretty(val):
    return "{}".format(val).rstrip('0').rstrip('.')


def is_between(c, a, b):
    """Check if the unicode value of char c is between values of a and b."""
    u = unichr(c)
    return unichr(a) <= u and u <= unichr(b)


def latex_escape(val):
    tbl = escape_table[TYPE_LATEX]
    return u"".join(tbl.get(x, x) for x in val)


def parse_latex_params(val):
    """Parse the content of [...]."""
    # Values with a comma not supported.
    result = {}
    for pair in val.split(','):
        if not pair.strip():
            continue
        try:
            name, val = pair.split('=')
        except ValueError:
            raise BBCodeException(_("Invalid format:") + " " + val)
        result[name.strip()] = val.strip()
    return result


# https://en.wikibooks.org/wiki/LaTeX/Lengths#Units
# Each TeX pt is converted to (72 / 72.27) CSS pts.
# <TeX unit>: (<length factor>, <HTML unit>)
_TEX_PT_TO_HTML = 72 / 72.27
_convert_tex_length_to_html__map = {
    'pt': (_TEX_PT_TO_HTML, 'pt'),
    'mm': None,
    'cm': None,
    'in': None,
    'ex': None,
    'em': None,
    'bp': (1. / 72, 'in'),
    'pc': (12 * _TEX_PT_TO_HTML, 'pt'),
    'dd': (1238 / 1157 * _TEX_PT_TO_HTML, 'pt'),
    'cc': (12 * 1238 / 1157 * _TEX_PT_TO_HTML, 'pt'),
    'sp': (_TEX_PT_TO_HTML / 65536., 'pt'),
}
def convert_tex_length_to_html(value):
    value = value.strip()
    try:
        length = float(value[:-2])
        unit = value[-2:]
        conversion = _convert_tex_length_to_html__map[unit]
    except (KeyError, ValueError):
        raise LatexValueError(_("Unexpected value:") + value)

    if conversion is None:
        return value  # Nothing to change.
    return "{:.9}{}".format(conversion[0] * length, conversion[1])


# def read_until(T, i, begin_pattern, end_pattern):
#     """Return everything until the matching end_pattern. Final index
#     points at the first character of the pattern.
#
#     Set begin_pattern to None to disable depth counting (i.e. recursive
#     commands).
#
#     Returns (i, content)."""
#     start = i
#     depth = 1
#     while i < len(T):
#         current = T[i];
#         if current == end_pattern[0] and \
#                 startswith_ex(T, i, end_pattern):
#             if depth == 1:
#                 return i, T[start:i]
#             depth -= 1
#         elif begin_pattern and current == begin_pattern[0] and \
#                 startswith_ex(T, i, begin_pattern):
#             depth += 1
#         elif startswith_ex(T, i, '\\url{'):
#             # This fixes just a single case where % doesn't actually
#             # represent a comment.
#             i, dummy = self.read_until_curly_brace(
#                     i + len('\\url{'), comments_enabled=False)
#         elif current == '%':
#             while i < len(T) and T[i] not in '\r\n':
#                 i += 1
#         elif current == '\\':
#             i += 2
#         else:
#             i += 1
#     raise ParseError(_("Matching \"%s\" not found.") % end_pattern)

########################################################
# Tag/command-specific helper functions
########################################################
def bb_code_link(type, url, content):
    """Output the <a...>...</a> tag or  \\url{...} or \\href{...}{...} command.

    Content will be used as the url if the 'url' is empty.
    """
    if type == TYPE_HTML:
        return u'<a href="{}" rel="nofollow">{}</a>'.format(
                xss.escape(url or content), content)
    if type == TYPE_LATEX:
        if url:
            return u'\\href{%s}{%s}' % (latex_escape(url), content)
        else:
            return u'\\url{%s}' % latex_escape(content)


def _img_parse_length(value):
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
    for name, value in params.iteritems():
        name = name.lower()
        if name == 'width':
            width = _img_parse_length(value)
        elif name == 'height':
            height = _img_parse_length(value)
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


def img_params_to_latex(params):
    out = {}
    scale = []
    for name, value in params.iteritems():
        name = name.lower()
        value = (value or '').strip()
        if name in ['width', 'height']:
            if value[-1] == '%':
                try:
                    scale.append(str(float(value[:-1])))
                except ValueError:
                    raise ParseError(_("Expected a number."))
            else:
                out[name] = str(_img_parse_length(value)) + 'pt'
        elif name == 'scale':
            try:
                scale.append(str(float(value)))
            except ValueError:
                raise ParseError(_("Expected a number."))
        elif name != 'attachment' and name != 'img':
            raise ParseError(_("Unexpected attribute:") + " " + name)
    if any(x != scale[0] for x in scale):
        raise ParseError(_("Incompatible scaling."))
    if scale:
        out['scale'] = scale[0]
    if out:
        result = u",".join(
                "{}={}".format(key, value) for key, value in out.iteritems())
        return "[{}]".format(result)
    else:
        return ""



########################################################
# Commands
########################################################
def _parse_argument__url(tokenizer):
    T = tokenizer.T
    K = tokenizer.K
    start = K
    braces = 0
    while K < len(T):
        if T[K] == '}':
            if braces == 0:
                K += 1
                break
            braces -= 1
        elif T[K] == '{':
            braces += 1
        K += 1
    tokenizer.K = K
    if braces > 0:
        return TokenError(_("Closing '}' bracket not found."), T[start : K])
    return T[start : K - 1]  # Don't include }.


class Command(object):
    def __init__(self, args_desc=""):
        """Args descriptor is a string of format <X><Y>...<Z>, where
        < > stands for [ ] or { }, and X for one of the following:
            P - parse ({} only)
            U - read as an URL ({} only)
            S - read until ']', but escaping \\\\ and \\] ([] only)

        Also, [...] brackets are treated as optional parameters."""

        assert len(args_desc) % 3 == 0
        self.argc = len(args_desc) / 3
        self.args_desc = args_desc

        # Example:
        # Argument index:   0  1  2  3  4  5  6  7
        # Argument descr:  [U]{U}{P}{P}{U}{U}{P}{U}
        # Part index:      0000000 11 22222222 3333
        # P_indices = [-1, 2, 3, 6, 8]  (8 == argc)
        mid = [k for k in range(self.argc) if args_desc[3 * k + 1] == 'P']
        self.P_indices = [-1] + mid + [self.argc]

    def __eq__(self, other):
        return _test_eq(self, other)

    def get_arg_open_bracket(self, index):
        assert index < self.argc
        return self.args_desc[3 * index]

    def parse_argument(self, tokenizer, name, index):
        """Default argument parsing method."""
        assert index < self.argc
        open, method, closed = self.args_desc[3 * index : 3 * index + 3]
        if method == 'P':
            assert open == '{' and closed == '}'
            tokenizer.push_state(State(break_condition=TOKEN_CLOSED_CURLY))
            return tokenizer.parse()
        if method == 'U':
            assert open == '{' and closed == '}'
            return _parse_argument__url(tokenizer)
        if method == 'S':
            assert open == '[' and closed == ']'
            return tokenizer.read_until(']', [r'\\', r'\]'])

    def apply_command(self, tokenizer, name, args, whitespace):
        """Manually add states or control tokenizer, or return tokens to be
        added. By default, add all parts that have been parsed and all
        TokenCommand in between and at the beginning and at the end of the
        command."""

        tokenizer.state.add_token(TokenCommand(name, 0, args, whitespace))
        for part in range(1, len(self.P_indices) - 1):
            tokenizer.state.add_token(args[self.P_indices[part]])
            tokenizer.state.add_token(
                    TokenCommand(name, part, args, whitespace))

    def to_html(self, token, converter):
        raise NotImplementedError(repr(token))

    def to_latex(self, token, converter):
        """Given a TokenCommand instance, generate LaTeX.

        By default it basically just reproduces the original input."""
        part = token.part
        output = []
        if token.part == 0:
            output.append('\\' + token.command)
            if self.argc == 0:
                output.append(token.whitespace[0])
        else:
            output.append('}')  # Close previous part.

        # Between previous and next P:
        for k in range(self.P_indices[part] + 1, self.P_indices[part + 1]):
            output.append(token.whitespace[k])
            if token.args[k] is None:
                continue
            open, method, closed = self.args_desc[3 * k : 3 * k + 3]
            assert method == 'S' or method == 'U'
            output.append(open + token.args[k] + closed)

        if part < len(self.P_indices) - 2:
            output.append(token.whitespace[self.P_indices[part + 1]])
            output.append('{')
        return u"".join(output)



class LatexBegin(Command):
    # TODO: \begin[...]{equation} ... \end{equation}
    # TODO: \begin{equation} ... \end{equation}
    def __init__(self):
        # SIMPLIFICATION MARK: Ignoring comments, using U.
        super(LatexBegin, self).__init__(args_desc="{U}")

    def apply_command(self, tokenizer, name, args, whitespace):
        """Simply add itself to the current state."""
        if args[0] not in latex_environments:
            return TokenError(_("Unknown LaTeX environment."), args[0])

        # Generate new LatexEnvironment instance.
        environment = latex_environments[args[0]]()

        # Pass environment as the arg.
        tokenizer.state.add_token(
                TokenCommand(name, 0, [args[0], environment], whitespace))
        tokenizer.push_state(State(break_condition='begin-' + args[0],
                environment=environment))

    def to_html(self, token, converter):
        environment = token.args[1]
        return environment.to_html(True, token, converter)



class LatexEnd(Command):
    # In the current implementation, \end{...} doesn't have the access to the
    # [...] arguments of \begin[...]{...}. (That's not so difficult to fix
    # if necessary)

    # TODO: \begin{equation} ... \end{equation}
    def __init__(self):
        # SIMPLIFICATION MARK: Ignoring comments, using U.
        super(LatexEnd, self).__init__(args_desc="{U}")

    def apply_command(self, tokenizer, name, args, whitespace):
        """Simply add itself to the current state."""
        break_condition = tokenizer.state.break_condition
        if not isinstance(break_condition, basestring) or \
                not break_condition.startswith('begin-'):
            return TokenError(_("Unexpected \\end."), "")
        expected = break_condition[6:]
        if expected != args[0]:
            return TokenError(
                    _("Expected '%(expected)s', received '%(received)s'.") %
                            {'expected': expected, 'received': args[0]}, "")
        environment = tokenizer.state.environment
        assert environment is not None
        result = tokenizer.pop_state().tokens
        return [
                result,
                TokenCommand(name, 0, [args[0], environment], whitespace)
        ]

    def to_html(self, token, converter):
        environment = token.args[1]
        return environment.to_html(False, token, converter)



class LatexCaption(Command):
    """Handle \\caption{...}."""
    def __init__(self):
        super(LatexCaption, self).__init__(args_desc="{P}")

    def apply_command(self, tokenizer, name, args, whitespace):
        # SIMPLIFICATION MARK - Not sure, but probably.
        if not hasattr(tokenizer.state.environment, 'tag'):
            return TokenError(_("Unexpected \\caption."), "")

        tokenizer.counters[COUNTER_FIGURE] += 1
        tag = str(tokenizer.counters[COUNTER_FIGURE])
        tokenizer.state.environment.tag = tag
        return super(LatexCaption, self).apply_command(
                tokenizer, name, args + [tag], whitespace)

    def to_html(self, token, converter):
        if token.part == 0:
            # TODO: Translation to other languages.
            tag_text = u"Slika {}:".format(token.args[-1])
            return u'<div class="mc-caption">' \
                    '<span class="mc-caption-tag">{}</span> '.format(tag_text)
        return '</div>'

    # def contribute(self, converter, name, content, params):
    #     block = converter.block_stack[-1]
    #     if block.name != 'figure':
    #         msg = _("\\caption supported only inside a 'figure' environment.")
    #         raise ParseError(msg)
    #     converter.counters[COUNTER_FIGURE] += 1
    #     tag = str(converter.counters[COUNTER_FIGURE])
    #     block.variables['tag'] = tag
    #     if converter.type == TYPE_HTML:
    #         # TODO: Translation to other languages.
    #         tag = u"Slika {}:".format(tag)
    #         return u'<div class="mc-caption">' \
    #                 '<span class="mc-caption-tag">{}</span> {}</div>'.format(
    #                         tag, content)
    #     elif converter.type == TYPE_LATEX:
    #         return r"\caption{" + content + "}"



class LatexCentering(Command):
    """Set block variable 'centering' to True."""
    def __init__(self):
        super(LatexCentering, self).__init__()

    def apply_command(self, tokenizer, name, args, whitespace):
        environment = tokenizer.state.environment
        if environment and hasattr(environment, 'centering'):
            environment.centering = True
            return TokenCommand('centering', 0, whitespace=whitespace)
        else:
            return TokenError(_("Unexpected \\centering."), "")

    def to_html(self, token, converter):
        return u""

    # def contribute(self, converter, name, content, params):
    #     converter.block_stack[-1].variables['centering'] = True
    #     if converter.type == TYPE_HTML:
    #         return ""
    #     elif converter.type == TYPE_LATEX:
    #         return r"\centering"



class LatexContainer(Command):
    def __init__(self, html_open, html_close):
        super(LatexContainer, self).__init__(args_desc="{P}")
        self.html_open = html_open
        self.html_close = html_close

    # def apply_command(self, tokenizer, name, args):
    #     # Do not pass arguments, we do not need them there.
    #     tokenizer.state.add_token(TokenCommand(name, 0))
    #     tokenizer.state.add_token(args[0])
    #     tokenizer.state.add_token(TokenCommand(name, 1))

    def to_html(self, token, converter):
        return self.html_open if token.part == 0 else self.html_close



class LatexHref(Command):
    def __init__(self):
        super(LatexHref, self).__init__(args_desc="{U}{P}")

    # def parse_argument(self, tokenizer, name, index):
    #     """Parse first argument as an URL, second normally."""
    #     if index == 0:
    #         return _parse_argument__url(tokenizer)
    #     return super(LatexHref, self).parse_argument(tokenizer, name, index)

    def to_html(self, token, converter):
        if token.part == 0:
            return u'<a href="{}" rel="nofollow">'.format(
                xss.escape(token.args[0]))
        else:
            return '</a>'
    # def contribute(self, converter, name, contents, params):
    #     url, desc = contents
    #     if converter.type == TYPE_HTML:
    #     elif converter.type == TYPE_LATEX:
    #         return u'\\href{%s}{%s}' % (latex_escape(url), latex_escape(desc))



class LatexIncludeGraphics(Command):
    def __init__(self):
        # SIMPLIFICATION MARK - We don't ignore comments here, because
        # whitespace handling seems also complicated, not to mention commands.
        super(LatexIncludeGraphics, self).__init__(args_desc='[S]{U}')

    def to_html(self, token, converter):
        # TODO: always send the list of attachments to the converter
        if converter.attachments is None:
            return TokenError(_("Attachments not shown in a preview."), "")
        filename = token.args[1]
        try:
            attachment = converter.attachments_dict[filename]
        except KeyError:
            return TokenError(_("Attachment not found:"), content.strip())

        params = parse_latex_params(token.args[0] or '')
        return u'<img src="{}" alt="Attachment {}" class="latex"{}>'.format(
                xss.escape(attachment.get_url()),
                xss.escape(filename),
                img_params_to_html(params))



class LatexInlineMathCommand(Command):
    """Command to be treated as an inline math when generating HTML, where it is
    replaced with $\\<command name>$. Leaves as-is when generating LaTeX."""
    def __init__(self, format, content):
        super(LatexInlineMathCommand, self).__init__()
        self.format = format
        self.content = content

    def to_html(self, token, converter):
        # Handled manually in Converter.
        raise ParserInternalError(
                "LatexInlineMathCommand.to_html is unreachable.")



class LatexLabel(Command):
    """Handle \\label{...}."""
    def __init__(self):
        super(LatexLabel, self).__init__(args_desc="{U}")

    def apply_command(self, tokenizer, name, args, whitespace):
        # SIMPLIFICATION MARK - Possibly labels don't work this way.
        environment = tokenizer.state.environment

        # HTML-only error.
        if not hasattr(environment, 'tag'):
            error = TokenError(_("Unexpected '\\label'."), "")
        elif environment.tag is None:
            error = TokenError(
                    _("Tag missing, did you put \\label before \\caption?"), "")
        else:
            error = u""
        tokenizer.refs[args[0]] = environment.tag
        return TokenCommand(name, 0, args + [error], whitespace)

    def to_html(self, token, converter):
        return token.args[-1]

    # def contribute(self, converter, name, content, params):
    #     block = converter.block_stack[-1]
    #     if 'tag' in block.variables:
    #         block.variables['label'] = content
    #         warning = u""
    #     else:
    #         msg = _(r"No tag set. Maybe \caption was written after \label?")
    #         warning = converter.warning(msg)

    #     if converter.type == TYPE_HTML:
    #         return warning
    #     elif converter.type == TYPE_LATEX:
    #         return warning + r"\label{" + content + "}"



class LatexNoop(Command):
    """Ignored when converting to HTML, printed without any logic when
    converting to LaTeX. Used for commonly used commands whose purpose is
    specific to LaTeX."""
    def __init__(self):
        super(LatexNoop, self).__init__()

    def to_html(self, token, converter):
        return ""



class LatexRef(Command):
    """Manually processed by Converter."""
    def __init__(self):
        super(LatexRef, self).__init__(args_desc="{U}")

    def to_html(self, token, converter):
        raise ParserInternalError("LatexRef.to_html is unreachable.")



class LatexSetLength(Command):
    """Set length of the given property. Limited to very few properties."""
    def __init__(self):
        super(LatexSetLength, self).__init__(args_desc="{U}{U}")

    def to_html(self, token, converter):
        var = token.args[0].strip()
        if var not in converter.state.lengths_html:
            msg = _("Unsupported value \"%(value)s\" for the command \"%(cmd)s\".")
            raise LatexValueError(msg % {'cmd': '\\setlength', 'value': var})
        converter.state.lengths_html[var] = \
                convert_tex_length_to_html(token.args[1])



class LatexSpecialSymbol(Command):
    def __init__(self, html):
        super(LatexSpecialSymbol, self).__init__()
        self.html = html

    def __repr__(self):
        return "LatexSpecialSymbol({})".format(repr(self.html))

    def to_html(self, token, converter):
        return self.html



class LatexURL(Command):
    def __init__(self):
        super(LatexURL, self).__init__(args_desc="{U}")

    def to_html(self, token, converter):
        url = xss.escape(token.args[0])
        return u'<a href="{}" rel="nofollow">{}</a>'.format(url, url)


########################################################
# LaTeX Environments
########################################################

class LatexEnvironment(object):
    def __eq__(self, other):
        return _test_eq(self, other)



class LatexEnvironmentDiv(LatexEnvironment):
    def __init__(self, html_class):
        super(LatexEnvironmentDiv, self).__init__()
        self.html_class = html_class

    def __repr__(self):
        return 'LatexEnvironmentDiv({})'.format(repr(self.html_class))

    def to_html(self, begin, token, converter):
        if begin:
            converter.push_state()
            converter.state.is_in_paragraph = False
            converter.state.all_no_indent = True
            return u'<div class="{}">'.format(self.html_class)
        else:
            converter.pop_state()
            converter.state.is_in_paragraph = False
            converter.state.indent_next = False
            return "</div>"



def latex_environment_div_factory(html_class):
    return lambda : LatexEnvironmentDiv(html_class=html_class)




# class LatexEnvironmentEquation(Command):
#     """Fixes the \\begin{equation}...\\end{equation} number."""
#     def __init__(self):
#         super(LatexEnvironmentEquation, self).__init__(parse_content=False)
#
#     def contribute(self, converter, name, content, params):
#         converter.counters[COUNTER_EQUATION] += 1
#         converter.extract_labels_from_mathmode(content, COUNTER_EQUATION)
#         if converter.type == TYPE_HTML:
#             latex = u"\\begin{equation}\\tag{%d}%s\\end{equation}" % \
#                     (converter.counters[COUNTER_EQUATION], content)
#             return u'<div class="mc-center">{}</div>'.format(
#                     converter.convert_latex_formula('%s', latex))
#         if converter.type == TYPE_LATEX:
#             # Return whatever here is.
#             if params:
#                 params = '[' + params + ']'
#             return u'\\begin{%s}%s%s\\end{%s}' % (name, params, content, name)



class LatexEnvironmentFigure(LatexEnvironment):
    """Handles \\begin{figure}...\\end{figure}."""
    def __init__(self, centering=False, tag=None):
        super(LatexEnvironmentFigure, self).__init__()
        self.centering = centering
        self.tag = tag

    def __repr__(self):
        return u'LatexEnvironmentFigure(centering={}, tag={})'.format(
                self.centering, repr(self.tag))

    def to_html(self, begin, token, converter):
        if begin:
            if self.centering:
                return u'<div class="mc-figure mc-center">'
            return u'<div class="mc-figure">'
        return u'</div>'


    # def contribute(self, converter, name, content, params):
    #     if converter.type == TYPE_HTML:
    #         if converter.block_stack[-1].variables.get('centering'):
    #             center = " mc-center"
    #         else:
    #             center = ""
    #         return u'<div class="mc-figure{}">{}</div>'.format(center, content)
    #     if converter.type == TYPE_LATEX:
    #         # Return whatever here is.
    #         if params:
    #             params = '[' + params + ']'
    #         return u'\\begin{%s}%s%s\\end{%s}' % (name, params, content, name)



########################################################
# BBCode
########################################################

def parse_bbcode(T, K):
    """Parse the following format:
        [tag_name var1=value1 var2=value2...]
    where `tag_name` is a sequence of alphanumeric characters, and `value` a
    sequence of non-whitespace non-] characters, or any characters wrapped in
    "..." or '...'. The quotation marks are escaped using \\", \\' and \\\\.
    Characters [ and ] shouldn't be escaped if inside quotation marks.

    Returns tag_name, open (True/False), {attr_name: value}, K
    (tag_name is also included in the dict in the middle)
    """
    assert T[K] == '['
    K += 1
    if K < len(T):
        open = T[K] != '/'
        if not open:
            K += 1

    tag_name = None
    attrs = {}
    while K < len(T) and T[K] != ']':
        while K < len(T) and T[K].isspace():
            K += 1  # Skip whitespace.

        # Read the variable name
        start = K
        while K < len(T) and T[K].isalnum():
            K += 1
        if K == start:
            # No special characters allowed in the variable name.
            raise BBCodeException()
        attr_name = T[start : K]
        if tag_name is None:
            tag_name = attr_name
        elif not open:
            raise BBCodeException()

        while K < len(T) and T[K].isspace():
            K += 1  # Skip whitespace.

        # Read the value.
        if T[K] == '=':
            if not open:
                raise BBCodeException()
            K += 1
            while K < len(T) and T[K].isspace():
                K += 1  # Skip whitespace.
            if T[K] in '\'"':
                quot = T[K]
                K += 1
                value = []
                while K < len(T) and T[K] != quot:
                    if T[K] == '\\' and K + 1 < len(T) and \
                            (T[K + 1] == '\\' or T[K + 1] == quot):
                        value.append(T[K + 1])
                        K += 2
                    else:
                        value.append(T[K])
                        K += 1
                if K == len(T):
                    raise BBCodeException()
                K += 1
                attrs[attr_name] = u"".join(value)
            else:
                start = K
                while K < len(T) and T[K] not in ' \t\r\n]':
                    K += 1
                attrs[attr_name] = T[start : K]
        else:
            attrs[attr_name] = None
    if K == len(T):
        raise BBCodeException()

    return tag_name, (attrs if open else None), K + 1



class BBCodeTag(object):
    def __init__(self, has_close_tag=True):
        self.has_close_tag = has_close_tag

    def should_parse_content(self, token):
        """Some tags might have parsing enabled or disabled depending on the
        attributes (e.g. [url]not parsed[/url], [url=...]parsed[/url]).
        Return True to use normal LaTeX parses, False to read until the end
        tag. """
        raise NotImplementedError()



class BBCodeContainer(BBCodeTag):
    def __init__(self, html_open, html_close, latex_open, latex_close):
        super(BBCodeContainer, self).__init__()
        self.html_open = html_open
        self.html_close = html_close
        self.latex_open = latex_open
        self.latex_close = latex_close

    def should_parse_content(self, token):
        return True

    def to_html(self, token, converter):
        if token.is_open():
            if len(token.attrs) != 1 or token.attrs.values()[0] is not None:
                raise BBCodeException(_("Unexpected parameter(s)."))
            return self.html_open
        return self.html_close

    def to_latex(self, token, converter):
        if token.is_open():
            if len(token.attrs) != 1 or token.attrs.values()[0] is not None:
                raise BBCodeException(_("Unexpected parameter(s)."))
            return self.latex_open
        return self.latex_close



class BBCodeImg(BBCodeTag):
    def __init__(self):
        super(BBCodeImg, self).__init__(has_close_tag=False)

    def _check(self, token, converter):
        if converter.attachments is None:
            return converter.warning(_("Attachments not shown in a preview."))
        if token.attrs['img'] is not None:  # "img" attribute should be None.
            raise BBCodeException(_("Unexpected parameter:") + " " + "img")
        try:
            val = token.attrs['attachment'].strip()
            index = int(val) - 1
            attachment = converter.attachments[index]
        except KeyError:
            raise BBCodeException(_("Missing an attribute:") + " attachment")
        except ValueError:
            msg = _(u'Invalid value "%(val)s" for the attribute "%(attr)s".')
            raise BBCodeException(msg % {'val': val, 'attr': 'attachment'})
        except IndexError:
            raise BBCodeException(_("Unavailable attachment:") + " " + val)
        return val, index, attachment

    def to_html(self, token, converter):
        val, index, attachment = self._check(token, converter)
        return u'<img src="{}" alt="Attachment #{}" class="latex"{}>'.format(
                xss.escape(attachment.get_url()), val,
                img_params_to_html(token.attrs))

    def to_latex(self, token, converter):
        val, index, attachment = self._check(token, converter)
        return u'\\includegraphics%s{%s}' % \
                (img_params_to_latex(token.attrs), attachment.get_filename())



# class BBCodeRef(BBCodeTag):
#     """Handle [ref=<tag> task=<task_id> page=<page>]link desc[/ref].
#
#     [ref...]...[/ref] is a skoljka-specific tag for referencing an external
#     formula or figure (any \\label{...}).
#     Attribute 'page' is optional, it adds #page=<page> to the link.
#     """
#     def contribute(self, converter, name, content, attributes):
#         attributes = dict(attributes)
#         ref = attributes.pop('ref', None)  # Tag.
#         task_id = attributes.pop('task', None)
#         if ref is None:
#             return converter.warning(_("Missing an attribute:") + " 'ref'")
#         if task_id is None:
#             return converter.warning(_("Missing an attribute:") + " 'task'")
#         page = attributes.pop('page', None)  # Optional.
#         page = "?page=" + page if page else ""
#         url = converter.get_full_url('/task/{}/ref/{}'.format(task_id, page))
#         if not content:
#             content = "(link)"
#         return converter.convert_latex_formula('$%s$', ref) + \
#                 bb_code_link(converter.type, url, content)



class BBCodeURL(BBCodeTag):
    def should_parse_content(self, token):
        # [url=...]...[/url --> parse normally
        # [url]...[/url] --> no parsing, read until [/url]
        return token.attrs['url'] is not None

    def to_html(self, token, converter):
        if token.is_open():
            if len(token.attrs) > 1:
                raise BBCodeException(_("Unexpected parameter(s)."))
            if token.content is not None:
                return u'<a href="{}" rel="nofollow">{}</a>'.format(
                        xss.escape(token.content), xss.escape(token.content))
            return u'<a href="{}" rel="nofollow">'.format(
                    xss.escape(token.attrs['url']))
        return '</a>'

    def to_latex(self, token, converter):
        if token.is_open():
            if len(token.attrs) > 1:
                raise BBCodeException(_("Unexpected parameter(s)."))
            if token.content is not None:
                # [url]...[/url]
                return u'\\url{%s}' % latex_escape(token.content)
            # [url=...]
            return u'\\href{%s}{' % latex_escape(token.attrs['url'])
        # [/url]
        return '}'



latex_commands = {
    '-': LatexSpecialSymbol('&shy;'),  # Soft hyphen.
    'LaTeX': LatexInlineMathCommand('%s', '\\LaTeX'),
    'TeX': LatexInlineMathCommand('%s', '\\TeX'),
    '\\': LatexSpecialSymbol('<br>'),
    'begin': LatexBegin(),
    'caption': LatexCaption(),
    'centering': LatexCentering(),
    'end': LatexEnd(),
    'emph': LatexContainer('<em>', '</em>'),
#     # TODO: eqref
    'fbox': LatexContainer('<span class="mc-fbox">', '</span>'),
    'href': LatexHref(),
    'includegraphics': LatexIncludeGraphics(),
    'label': LatexLabel(),
    'mbox': LatexContainer('<span class="mc-mbox">', '</span>'),
    'ref': LatexRef(),
    'setlength': LatexSetLength(),
    'sout': LatexContainer('<s>', '</s>'),
    'textasciicircum': LatexSpecialSymbol('^'),
    'textasciitilde': LatexSpecialSymbol('~'),  # Not really.
    'textbackslash': LatexSpecialSymbol('\\'),
    'textbf': LatexContainer('<b>', '</b>'),
    'textit': LatexContainer('<i>', '</i>'),
    'uline': LatexContainer('<u>', '</u>'),
    'underline': LatexContainer('<span class="mc-underline">', '</span>'),
    'url': LatexURL(),
    '~': LatexSpecialSymbol('~'),  # NOT FULLY IMPLEMENTED.
}

latex_environments = {
    'center': latex_environment_div_factory('mc-center'),
    'equation': None, # LatexEnvironmentEquation(),
    'figure': LatexEnvironmentFigure,
    'flushleft': latex_environment_div_factory('mc-flushleft'),
    'flushright': latex_environment_div_factory('mc-flushright'),
}

bb_commands = {
    'b': BBCodeContainer('<b>', '</b>', '\\textbf{', '}'),
    'center': BBCodeContainer('<div class="mc-center">', '</div>',
                              '\\begin{center}', '\\end{center}'),
    'i': BBCodeContainer('<i>', '</i>', '\\textit{', '}'),
    'img': BBCodeImg(),
    # TODO: Quote for LaTeX.
    'quote': BBCodeContainer('<div class="mc-quote">', '</div>', '', ''),
    # 'ref': BBCodeRef(),
    's': BBCodeContainer('<s>', '</s>', '\\sout{', '}'),
    'u': BBCodeContainer('<u>', '</u>', '\\uline{', '}'),
    'url': BBCodeURL(),
}


########################################################
# Tokenizer
########################################################

class State(object):
    def __init__(self, break_condition=None, environment=None):
        self.tokens = []
        self.break_condition = break_condition
        self.environment = environment  # LatexEnvironment instance.

    def add_token(self, tokens):
        self.tokens.append(tokens)  # Flatten later.


class Tokenizer(object):
    def __init__(self, T):
        self.T = T.strip()
        # self.bbcode = True
        self.K = 0
        self.state = State()
        self.state_stack = [self.state]

        self.counters = defaultdict(int)
        self.refs = {}      # References, dict label -> tag.

        self._last_token = None
        self._undoed_token = None

    def push_state(self, state):
        self.state_stack.append(state)
        self.state = state

    def pop_state(self):
        """Pop current state and return it."""
        if len(self.state_stack) < 2:
            raise ParserInternalError("State stack has too few elements.")
        self.state = self.state_stack[-2]
        return self.state_stack.pop()


    def get_full_url(self, url):
        return urljoin(self.url_prefix, url)

    def get_latex_picture(self, *args, **kwargs):
        # To be able to mock it.
        return get_latex_picture(*args, **kwargs)

    def _nt__read_text(self):
        """(next_token helper function) Read everything until any of the
        `end_char` characters is reached.  The end character is not read."""
        T = self.T
        K = self.K
        start = K
        while K < len(T) and T[K] not in _NT__READ_TEXT__END_CHAR:
            K += 1
        if K < len(T):
            # Don't include the whitespace at the end.
            while K > start and T[K - 1].isspace():
                K -= 1
        self.K = K
        return T[start : K]

    def _nt__read_whitespace(self):
        """(next_token helper function) Read until a non-whitespace character
        is found (doesn't read that character). Counts properly the number of
        line breaks."""
        T = self.T
        K = self.K
        start = K
        line_breaks = 0
        while K < len(T) and T[K].isspace():
            if T[K] in '\r\n':
                if T[K : K + 2] == '\r\n':
                    K += 1
                line_breaks += 1
            K += 1
        self.K = K
        return T[start : K], line_breaks

    def _nt__read_command_name(self):
        """(next_token helper function) Read command name according to
        http://tex.stackexchange.com/a/66671 """
        T = self.T
        K = self.K
        assert K < len(T)
        start = K
        if RE_ASCII_ALPHA_SINGLE_CHAR.match(T[K]):
            # Any number of [a-zA-Z] characters.
            K += 1
            while K < len(T) and RE_ASCII_ALPHA_SINGLE_CHAR.match(T[K]):
                K += 1
        else:
            # Or a single non-[a-zA-Z] character.
            K += 1
        self.K = K
        return T[start : K]

    def _nt__read_comment(self):
        """(next_token helper function) Read until a newline and all whitespace
        after the newline."""
        T = self.T
        K = self.K
        start = K
        while K < len(T):
            if T[K] in '\r\n':
                K += 2 if T[K : K + 2] == '\r\n' else 1
                break
            K += 1
        while K < len(T) and T[K].isspace():
            K += 1
        self.K = K
        return T[start : K]


    def _next_token(self):
        """Get the next token. If the logic is trivial, immediately return a
        Token object, otherwise return (token_type, content) for the caller to
        handle it."""
        T = self.T
        K = self.K
        if K >= len(T):
            return None
        if T[K].isspace():
            whitespace, line_breaks = self._nt__read_whitespace()
            if line_breaks >= 2:
                return TokenMultilineWhitespace(whitespace)
            # Unreachable code actually.
            return TokenSimpleWhitespace(whitespace)
        elif T[K] == '$' or T[K : K + 2] in [r'\(', r'\[']:
            return self.handle_math_mode()
        elif T[K] == '\\':
            self.K += 1
            if self.K == len(T):
                return TokenError("'\' character without a command name.")
            return TOKEN_COMMAND, self._nt__read_command_name()
        elif T[K] == '{':
            self.K += 1
            return TOKEN_OPEN_CURLY, '{'
        elif T[K] == '}':
            self.K += 1
            return TOKEN_CLOSED_CURLY, '}'
        elif T[K] == '[':
            self.K += 1
            return TOKEN_OPEN_SQUARE, '['
        elif T[K] == ']':
            self.K += 1
            return TOKEN_CLOSED_SQUARE, ']'
        elif T[K] == '%':
            self.K += 1
            return TokenComment(self._nt__read_comment())
        else:
            return TokenText(self._nt__read_text())

    def next_token(self):
        """Wrapper around real next token method, checks if the token was
        undoed."""
        if self._undoed_token:
            result = self._undoed_token
            self._undoed_token = None
            return result

        self._last_token = self._next_token()
        return self._last_token

    def undo_token(self):
        if self._undoed_token:
            raise ParserInternalError(
                    "Cannot perform undo twice in a row. Old={} New={}".format(
                        self._undoed_token, self._last_token))
        self._undoed_token = self._last_token


    def read_until(self, end, skip_patterns):
        """Read everything until `end` is reached. Skips all patterns in the
        list `skip_patterns`. The result doesn't contain `end`, but `end` itself
        is skipped.

        Low-level, doesn't use next_token."""
        # self._last_token = False
        # self._undoed_token = False  # Sorry, have to forget the last undo.

        T = self.T
        K = self.K
        start = K
        while K < len(T) and T[K : K + len(end)] != end:
            jump = 1
            for pattern in skip_patterns:
                if T[K : K + len(pattern)] == pattern:
                    jump = len(pattern)
                    break
            K += jump
        if T[K : K + len(end)] != end:
            raise LatexSyntaxError(_("Ending not found:") + " " + end)
        self.K = K + len(end)
        return T[start : K]

    def handle_math_mode(self):
        """Handle $...$, $$...$$, \(...\), \[...\] and $$$ ... $$$."""
        T = self.T
        K = self.K
        dollars = 0
        if T[K] == '$':
            while K < len(T) and dollars < 4 and T[K] == '$':
                dollars += 1
                K += 1
            if dollars == 4:  # Special case.
                self.K = K
                return TokenMath('$$%s$$', "")
            begin = '$' * dollars
            end = begin
        else:
            begin = self.T[K : K + 2]
            K += 2
            if begin == r'\(':
                end = r'\)'
            elif begin == r'\[':
                end = r'\]'
            else:
                raise ParserInternalError("Unreachable code. begin=" + begin)

        self.K = K
        latex = self.read_until(end, [r'\\', r'\$'])

        if begin == '$$$':
            format = '%s'
        else:
            format = begin + '%s' + end
        return TokenMath(format, latex)

    # def handle_square_bracket(self):
    #     # SIMPLIFICATION MARK - We don't parse the content.
    #     return self.read_until(']', [r'\\', r'\]'])

    # def handle_curly_bracket(self):
    #     """Read  "something}" after "}" is read."""
    #     self.push_state(end_token=TOKEN_CLOSED_CURLY)
    #     return self.parse()

    def handle_command(self, name):
        """Handle the logic of optional [] and mandatory {} arguments (this is
        our simplification) and call command.parse_argument(...) which performs
        the actual parsing. Command is performing the parsing because the
        syntax actually depends on the command itself. (e.g. \\url and \\href).
        """
        full_name = '\\' + name
        try:
            command = latex_commands[name]
        except KeyError:
            return TokenError(_("Unknown LaTeX command."), full_name)
        args = []
        whitespace = []  # One for each argument.
        # (in the case some arguments are not given, the order of whitespace
        # might be incorrect, but it won't affect the final LaTex output)

        # SIMPLIFICATION MARK - Maybe this isn't how it's supposed to work.
        # We allow complicated patterns like [][]{}{}[]{}.
        # [] represents here an optional parameter, {} mandatory.

        # Here len(args) == index of the current argument we are processing.
        start = self.K
        while len(args) < command.argc:
            # TODO: support \name <char><char> or \name<digit><char/digit><...>
            last_K = self.K
            token = self.next_token()
            # TODO: multiline whitespace
            if isinstance(token, TokenSimpleWhitespace):
                current_whitespace = token.text
                token = self.next_token()
            else:
                current_whitespace = ""

            if token is None or isinstance(token, Token):
                token_type = None
                content = None
            else:
                token_type, content = token

            expected_bracket = command.get_arg_open_bracket(len(args))
            if token_type == TOKEN_OPEN_SQUARE:
                if expected_bracket == '[':
                    # args.append(self.handle_square_bracket())
                    args.append(command.parse_argument(self, name, len(args)))
                    whitespace.append(current_whitespace)
                    if isinstance(args[-1], TokenError):
                        return args[-1]
                    continue
                else:
                    return TokenError(_("Expected a '{' bracket."),
                            full_name + self.T[start : last_K])
            while len(args) < command.argc and \
                    command.get_arg_open_bracket(len(args)) == '[':
                args.append(None)  # Skip optional arguments.
                whitespace.append(current_whitespace)
                current_whitespace = ""
            if len(args) == command.argc:
                self.undo_token()
                break
            if token_type == TOKEN_OPEN_CURLY:
                args.append(command.parse_argument(self, name, len(args)))
                whitespace.append(current_whitespace)
                if isinstance(args[-1], TokenError):
                    return args[-1]
                # args.append(self.handle_curly_bracket())
            else:
                self.undo_token()
                return TokenError(
                        _("Expected a '%s' bracket.") % expected_bracket,
                        full_name + self.T[start : last_K])

        # Manually handle no-argument commands and their trailing whitespace.
        if command.argc == 0:
            token = self.next_token()
            if isinstance(token, TokenSimpleWhitespace):
                whitespace = [token.text]
            else:
                whitespace = [""]
                self.undo_token()

        return command.apply_command(self, name, args, whitespace)


    def handle_bbcode(self):
        """Handle BBCode or do nothing. If BBCode is in any way invalid, the
        original text is shown without any errors or messages."""
        start = self.K - 1
        T = self.T
        try:
            name, attrs, K = parse_bbcode(T, start)
        except BBCodeException:
            return TokenText(u"[")  # Just print it as a normal string.
        if name not in bb_commands:
            return TokenText(u"[")

        token = TokenBBCode(name, attrs, start, K)
        command = bb_commands[name]
        if token.is_open() and command.has_close_tag and \
                not command.should_parse_content(token):
            end_pattern = '[/{}]'.format(name)
            content = []
            while K < len(T):
                if T[K] == '[':
                    if T[K : K + len(end_pattern)] == end_pattern:
                        break
                elif T[K] == '\\' and K + 1 < len(T) and T[K + 1] in '\\[':
                    # Escape \ and [.
                    K += 1
                content.append(T[K])
                K += 1
            if K == len(T):
                return TokenText(u"[")  # End tag missing.
            # This case will generate a single token, one for both open and
            # close tag.
            K += len(end_pattern)
            token.content = u"".join(content)

        self.K = K
        return token



    def parse(self):
        start = self.K
        last_K = None
        repeat_count = 0
        while True:
            if self.K <= last_K:
                repeat_count += 1
                if repeat_count > 1:    # Handle undo.
                    raise ParserInternalError(
                            "Infinite loop at K={}?".format(self.K))
            else:
                repeat_count = 0
            last_K = self.K

            token = self.next_token()
            if isinstance(token, Token):
                self.state.add_token(token)
                continue
            elif token is None:
                break

            type, content = token
            if type == TOKEN_COMMAND:
                final_token = self.handle_command(content)
            elif type == TOKEN_CLOSED_CURLY:
                if self.state.break_condition != TOKEN_CLOSED_CURLY:
                    final_token = TokenError(_("Unexpected '}'."), '}')
                elif len(self.state_stack) < 2:
                    final_token = ParserInternalError("Unexpected '}'.")
                else:
                    return self.pop_state().tokens
            elif type == TOKEN_OPEN_CURLY:
                self.push_state(State(break_condition=TOKEN_CLOSED_CURLY))
                final_token = [
                        TokenOpenCurly(),
                        self.parse(),
                        TokenClosedCurly()
                ]
            elif type == TOKEN_OPEN_SQUARE:
                final_token = self.handle_bbcode()
            elif type == TOKEN_CLOSED_SQUARE:
                final_token = TokenText("]")
            else:
                raise NotImplementedError(repr(token))

            self.state.add_token(final_token)

        if self.state.break_condition is not None:
            if self.state.break_condition == TOKEN_CLOSED_CURLY:
                msg = _("Expected a '}' bracket.")
            else:
                msg = _("End delimiter missing.")
            return [TokenError(msg, self.T[start : self.K])]
        return self.state.tokens

    def tokenize(self):
        tokens = list(flatten_ignore_none(self.parse()))
        # print
        # print "Tokenization"
        # print "-----------"
        # print self.T
        # print "-----------"
        # print repr(self.T)
        # print "-----------"
        # for token in tokens:
        #     print repr(token)
        return tokens

    # def convert(self):  # XSS danger!!! Be careful
    #     """Converts MathContent format to HTML (type 0) or LaTeX (type 1)

    #     To support special tags like [img], it must be called with a
    #     content instance."""

    #     self.K = 0
    #     return self.parse()


def get_latex_html(latex_element):
    """Given LatexElement instance generate <img> HTML."""
    inline = format in ['$%s$', '\(%s\)']
    latex_escaped = xss.escape(latex_element.text)
    depth = latex_element.depth

    if depth == ERROR_DEPTH_VALUE:
        # TODO: link to the log file.
        return u'<span class="mc-error-source" title="{}">{}</span>'.format(
                xss.escape(_("Invalid LaTeX.")),
                xss.escape(latex_element.format % latex_element.text))


    hash = latex_element.hash
    url = '%s%s/%s/%s/%s.png' % (IMG_URL_PATH, hash[0], hash[1], hash[2], hash)
    if inline:
        return u'<img src="%s" alt="%s" class="latex" ' \
                'style="vertical-align:%dpx">' % (url, latex_escaped, -depth)
    else:
        return u'<img src="%s" alt="%s" class="latex-center">' % \
                (url, latex_escaped)

    # # FIXME: don't save error message to depth
    # hash, depth = generate_svg(latex, format, inline)
    # if depth == ERROR_DEPTH_VALUE:
    #     # TODO: link to the log file.
    #     out.append('{{ INVALID LATEX }}')
    # else:
    #     url = '%s%s/%s/%s/%s.svg' % (IMG_URL_PATH, hash[0], hash[1], hash[2], hash)
    #     if inline:
    #         obj = '<object data="%s" type="image/svg+xml" alt="%s" class="latex" style="vertical-align:%fpt"></object>' % (url, latex_escaped, -depth)
    #     else:
    #         obj = '<object data="%s" type="image/svg+xml" alt="%s" class="latex_center"></object>' % (url, latex_escaped)
    return img


########################################################
# Converter
########################################################
class _BBTemporaryOpenTag(object):
    """Token marking the processed open BB tag, which has to wait to see if
    closing tag exists. If it exists, the token is replaced with .result,
    otherwise the original text is shown (.token has the interval of the
    original string)."""
    def __init__(self, result, token):
        self.result = result
        self.token = token
        self.approved = False

    def finalize(self, converter):
        if self.approved:
            return self.result
        return converter.tokenizer.T[self.token.T_start : self.token.T_end]


class Converter(object):
    def __init__(self, tokens, tokenizer, attachments=None,
            errors_enabled=True, paragraphs_disabled=False):
        # TODO: attachments_path
        # TODO: url_prefix (what is this?)

        # TODO: this makes no sense...
        self.tokens = tokens
        self.tokenizer = tokenizer
        self.refs = tokenizer.refs

        self.maths = None
        self.attachments = attachments
        self.attachments_dict = {x.get_filename(): x for x in attachments or []}
        self.errors_enabled = errors_enabled
        self.paragraphs_disabled = paragraphs_disabled

        self.generate_png__func = generate_png
        self.generate_latex_hash__func = generate_latex_hash
        self.get_available_latex_elements__func = get_available_latex_elements
        self.get_latex_html__func = get_latex_html

        self.bb_stack = []

        self._state_stack = []
        self.state = None

    def push_state(self):
        self._state_stack.append(copy.deepcopy(self._state_stack[-1]))
        self.state = self._state_stack[-1]

    def pop_state(self):
        self._state_stack.pop()
        self.state = self._state_stack[-1]

    def _pre_convert_to_html(self):
        # Here we process tokens of specific types before calling .to_html.
        # TokenCommand for LatexRef are replaced with TokenMath.
        formulas = []
        tokens = []
        for token in self.tokens:
            if isinstance(token, TokenCommand):
                command = latex_commands[token.command]
                if token.command == 'ref':
                    ref = self.refs.get(token.args[0])
                    token = TokenMath('$%s$', ref if ref is not None else '??')
                elif isinstance(command , LatexInlineMathCommand):
                    token = TokenMath(command.format, command.content)

            if isinstance(token, TokenMath):
                latex_hash = self.generate_latex_hash__func(
                        token.format, token.content)
                formulas.append((latex_hash, token.format, token.content))

            tokens.append(token)

        latex_elements = {x.hash: x \
                for x in self.get_available_latex_elements__func(formulas)}

        self.maths = {}
        for hash, format, content in formulas:
            element = latex_elements.get(hash)
            if element is None:
                element = self.generate_png__func(hash, format, content)
            self.maths[(format, content)] = element

        return tokens

    def process_bb(self, token, type):
        assert token.name in bb_commands
        bb = bb_commands[token.name]
        try:
            if token.is_open():
                if type == TYPE_HTML:
                    result = bb.to_html(token, self)
                else:
                    result = bb.to_latex(token, self)
                if isinstance(result, TokenError):
                    return result
                if bb.has_close_tag and token.content is None:
                    # If content isn't None, close tag has been parsed
                    # immediately, and there was only a single BB token added.
                    bb_token = _BBTemporaryOpenTag(result, token)
                    self.bb_stack.append(bb_token)
                    return bb_token
                else:
                    return result
            else:  # Closed tag.
                if not bb.has_close_tag or len(self.bb_stack) == 0 or \
                        not hasattr(self.bb_stack[-1], 'token') or \
                        getattr(self.bb_stack[-1].token, 'name', None) != \
                                token.name:
                    raise BBCodeException()
                self.bb_stack[-1].approved = True
                self.bb_stack.pop()
                if type == TYPE_HTML:
                    return bb.to_html(token, self)
                else:
                    return bb.to_latex(token, self)
        except BBCodeException as e:
            return TokenError(
                    e.msg, self.tokenizer.T[token.T_start : token.T_end])

    def finalize_output(self, output, error_func):
        # Conversion helper function can return TokenError. We convert them to
        # LaTeX here.
        final = []
        for x in output:
            if isinstance(x, _BBTemporaryOpenTag):
                x = x.finalize(self)
            if isinstance(x, TokenError):
                x = error_func(x)
            if isinstance(x, basestring):
                final.append(x)
            elif x is not None:
                raise ParserInternalError(
                        "Unrecognized value in the final step: " + repr(x))
        return u"".join(final)

    def convert_to_html(self):
        tokens = self._pre_convert_to_html()
        if self.errors_enabled:
            error_func = lambda token: u'<span class="mc-error">' \
                    u'<span class="mc-error-source">{}</span> {}</span>'.format(
                        token.content, token.error_message)
        else:
            error_func = lambda token: u""

        class HTMLConverterState(object):
            def __init__(self):
                self.is_in_paragraph = False
                self.indent_next = False
                self.all_no_indent = False

                # List of all supported lengths. None stands for the default
                # value. These are the HTML values.
                self.lengths_html = {'\\parindent': None, '\\parskip': None}


        self._state_stack = [HTMLConverterState()]
        self.state = self._state_stack[-1]

        output = []
        def add_content_par(content):
            """First check if paragraph should be added and then add content.
            No-op if content evaluates to False."""
            if not content:
                return

            state = self.state
            if not self.paragraphs_disabled and not state.is_in_paragraph:
                indent = state.indent_next and not state.all_no_indent

                css_class = ""
                css_style = ""
                parskip = state.lengths_html['\\parskip']
                if parskip is not None:
                    # It seems to be top, not bottom that's affected.
                    css_style += "margin-top:{};".format(parskip)

                if indent:
                    parindent = state.lengths_html['\\parindent']
                    if parindent is not None:
                        css_style += "text-indent:{};".format(parindent)
                    else:
                        css_class = "mc-indent"
                else:
                    css_class = "mc-noindent"

                output.append("<p{}{}>".format(
                    " class=\"{}\"".format(css_class) if css_class else "",
                    " style=\"{}\"".format(css_style) if css_style else ""))
            output.append(content)
            state.is_in_paragraph = True

        for token in tokens:
            if isinstance(token, TokenComment):
                continue
            elif isinstance(token, TokenOpenCurly):
                self.push_state()
            elif isinstance(token, TokenClosedCurly):
                if len(self._state_stack) == 1:
                    output.append(TokenError(_("Unexpected '}'"), '}'))
                else:
                    self.pop_state()
            elif isinstance(token, TokenMath):
                element = self.maths[(token.format, token.content)]
                add_content_par(self.get_latex_html__func(element))
            elif isinstance(token, TokenText):
                add_content_par(xss.escape(token.text))
            elif isinstance(token, TokenSimpleWhitespace):
                output.append(" ")  # Single whitespace is enough.
            elif isinstance(token, TokenMultilineWhitespace):
                if self.paragraphs_disabled:
                    output.append("<br>")
                else:
                    self.state.is_in_paragraph = False
                    self.state.indent_next = True
            elif isinstance(token, TokenError):
                add_content_par(error_func(token))
            elif isinstance(token, TokenCommand):
                command = latex_commands[token.command]
                # TODO: \begin{equation}...\end{equation}
                try:
                    if token.command in ['begin', 'end']:
                        output.append(command.to_html(token, self))
                    else:
                        add_content_par(command.to_html(token, self))
                except LatexValueError as e:
                    output.append(TokenError(e.message, '\\' + token.command))
            elif isinstance(token, TokenBBCode):
                output.append(self.process_bb(token, TYPE_HTML))
            else:
                raise NotImplementedError(repr(token))
        return self.finalize_output(output, error_func)

    def convert_to_latex(self):
        output = []
        if self.errors_enabled:
            error_func = lambda token: "\\textbf{%s} %s" % \
                    (token.error_message, token.content)
        else:
            error_func = lambda token: u""
        for token in self.tokens:
            if isinstance(token, (TokenText, TokenSimpleWhitespace, \
                    TokenMultilineWhitespace)):
                output.append(token.text)
            elif isinstance(token, TokenComment):
                output.append("%")
                output.append(token.text)
            elif isinstance(token, TokenMath):
                output.append(token.format % token.content)
            elif isinstance(token, TokenCommand):
                command = latex_commands[token.command]
                output.append(command.to_latex(token, self))
            elif isinstance(token, TokenError):
                output.append(error_func(token))
            elif isinstance(token, TokenOpenCurly):
                output.append('{')
            elif isinstance(token, TokenClosedCurly):
                output.append('}')
            elif isinstance(token, TokenBBCode):
                output.append(self.process_bb(token, TYPE_LATEX))
            else:
                raise NotImplementedError(repr(token))

        return self.finalize_output(output, error_func)



def convert(type, text, attachments=None, attachments_path=None, url_prefix=""):
    """Convert given text to the given type in the context of the given
    attachments."""
    # TODO: attachments_path
    # TODO: url_prefix (what is this?)
    tokenizer = Tokenizer(text)
    tokens = tokenizer.tokenize()

    converter = Converter(tokens, tokenizer, attachments=attachments)
    if type == TYPE_HTML:
        return converter.convert_to_html()
    else:
        return converter.convert_to_latex()

    # # converter = Converter(type, text, attachments, url_prefix=url_prefix)
    # try:
    #     i, output = converter.convert()
    # except Exception as e:
    #     msg = _("Error converting the text:") + " " + e.message
    #     return u'<span class="mc-error">{}</span>'.format(msg)
    # return output
