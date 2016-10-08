from django.utils.translation import ugettext as _

from skoljka.libs import flatten_ignore_none, xss

from mathcontent.models import ERROR_DEPTH_VALUE, IMG_URL_PATH, TYPE_HTML, \
        TYPE_LATEX
from mathcontent.latex import generate_png, generate_latex_hash, \
        get_available_latex_elements

from mathcontent.converter_v1.basics import State, ParseError
from mathcontent.converter_v1.tokens import Token, TokenText, TokenCommand, \
        TokenMultilineWhitespace, TokenSimpleWhitespace, TokenMath, \
        TokenError, TokenComment, TokenOpenCurly, TokenClosedCurly, \
        TokenBBCode
from mathcontent.converter_v1.tokens import TOKEN_COMMAND, TOKEN_OPEN_CURLY, \
        TOKEN_CLOSED_CURLY, TOKEN_OPEN_SQUARE, TOKEN_CLOSED_SQUARE
from mathcontent.converter_v1.bbcode import bb_commands, parse_bbcode, \
        BBCodeException
from mathcontent.converter_v1.latex import latex_commands, latex_escape_chars, \
        latex_environments, LatexValueError, LatexInlineMathCommand

from collections import defaultdict
from urlparse import urljoin

import copy
import re

# If changing these note that all the MathContents not setting these values
# manually will be affected. Also, don't forget to update mathcontent.scss
# (.mc-indent and .mc-preview p, .mc-inner p).
default_parskip = '1em'
default_parindent = '0em'


# FIXME: Converter crashes if $??$ from \ref{...} not already generated and
# appears multiple times in the text.

# TODO: Paragraphs!
#  E.g. [center]...[/center] should be equal to \begin{center}...\end{center}.
# TODO: Support for starred commands.
#  E.g. \\* which does nothing in HTML.
# TODO: \\[5pt]
# TODO: \newline
# TODO: \par
# TODO: Quotation marks ``text'' and `text' for HTML.
# TODO: \begin{enumerate} \item ... \end{enumerate}
# TODO: \begin{itemize} \item ... \end{itemize}
# TODO: \begin{description} \item[bla] ... \end{description}
# TODO: Support recursive enumerate / itemize / description.
# TODO: \begin{quote}...\end{quote}
# TODO: \begin{multline}...\end{multline}
# TODO: \begin{eqnarray}...\end{eqnarray}
# TODO: fix uline and sout --> support for custom usepackage
# TODO: \<space>, and \<end of line>

# MAYBE: \" \i \j \o \^ \ss \~ and other special characters
# MAYBE: \begin{verbatim}...\end{verbatim}
# MAYBE: \verb+asdf+
# MAYBE: \begin{verbatim*} and \verb*
# MAYBE: \newpage
# MAYBE: \(no)linebreak[n]
# MAYBE: \(no)pagebreak[n]
# MAYBE: \begin{comment}...\end{comment} with \usepackage{verbatim}


RE_ASCII_ALPHA_SINGLE_CHAR = re.compile('[a-zA-Z]')
_NT__READ_TEXT__END_CHAR = set('{}[]$\n\r\\%')


class ParserInternalError(Exception):
    pass


########################################################
# Tokenizer
########################################################

class Tokenizer(object):
    def __init__(self, T):
        self.T = T.strip()
        self.bbcode = True
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
        is skipped. Skips comments, but includes them in the return value.

        Low-level, doesn't use next_token."""
        # self._last_token = False
        # self._undoed_token = False  # Sorry, have to forget the last undo.

        T = self.T
        K = self.K
        start = K
        while K < len(T) and T[K : K + len(end)] != end:
            jump = 1
            if T[K] == '%':
                self.K = K
                self._nt__read_comment()
                K = self.K
                continue
            for pattern in skip_patterns:
                if T[K : K + len(pattern)] == pattern:
                    jump = len(pattern)
                    break
            K += jump
        if T[K : K + len(end)] != end:
            raise ParseError(_("Ending not found:") + " " + end)
        self.K = K + len(end)
        return T[start : K]

    def read_until_exact(self, end):
        """Read everything until `end` is reached, without any complications.
        The result doesn't contain `end`, but `end` itself is skipped.

        Low-level, doesn't use next_token."""
        start = self.K
        K = self.T.find(end, start)
        if K == -1:
            raise ParseError(_("Ending not found:") + " " + end)
        self.K = K + len(end)
        return self.T[start : K]

    def read_until_exact_any(self, endings):
        """Similar to read_until_exact, just picks the closest ending.
        Final ending not included in the result, but is skipped."""
        start = self.K
        minK = len(self.T)
        closest = None
        for end in endings:
            K = self.T.find(end, start)
            if K != -1 and K < minK:
                minK = K
                closest = end
        if not closest:
            raise ParseError(
                    _("None of the endings found:") + " " + u", ".join(end))
        self.K = K + len(end)
        return self.T[start : K]


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
        latex = self.read_until(end, [r'\\', r'\$', r'\%'])

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
        # Manually take care of escape characters, because they don't consume
        # the following whitespace.
        if name in latex_escape_chars:
            return TokenCommand(name, 0, [], [""])

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

        if self.bbcode:
            if T[self.K : self.K + 5] == "nobb]":
                self.bbcode = False
                self.K += 5
                return None
        else:
            if T[self.K : self.K + 6] == "/nobb]":
                self.bbcode = True
                self.K += 6
                return None
            return TokenText(u"[")

        try:
            name, attrs, K = parse_bbcode(T, start)
        except BBCodeException as e:
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
            try:
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
            except ParseError as e:
                self.state.add_token(TokenError(e.message, self.T[last_K:]))
                return self.state.tokens

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



def get_latex_html(latex_element, force_inline):
    """Given LatexElement instance generate <img> HTML."""
    inline = force_inline or latex_element.format in ['$%s$', '\(%s\)']
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
    #         obj = '<object data="%s" type="image/svg+xml" alt="%s" class="latex-center"></object>' % (url, latex_escaped)
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
    ERRORS_DISABLED = 0
    ERRORS_ENABLED = 1
    ERRORS_TESTING = 2

    def __init__(self, tokens, tokenizer, attachments=None,
            errors_mode=True, paragraphs_disabled=False):
        # TODO: attachments_path
        # TODO: url_prefix (what is this?)

        # TODO: this makes no sense...
        self.tokens = tokens
        self.tokenizer = tokenizer
        self.refs = tokenizer.refs

        self.maths = None
        self.attachments = attachments
        self.attachments_dict = {x.get_filename(): x for x in attachments or []}
        self.errors_mode = errors_mode
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
        self.state.any_content_yet = False

    def pop_state(self):
        was_content_yet = self.state.any_content_yet
        self._state_stack.pop()
        self.state = self._state_stack[-1]
        self.state.any_content_yet |= was_content_yet

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
                    token = TokenMath(command.format, command.content,
                            force_inline=True)

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
            return self.tokenizer.T[token.T_start : token.T_end]
            # Show no errors at all for now.
            # return TokenError(
            #         e.message, self.tokenizer.T[token.T_start : token.T_end])

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
        if self.errors_mode == Converter.ERRORS_ENABLED:
            error_func = lambda token: u'<span class="mc-error">' \
                    u'<span class="mc-error-source">{}</span> {}</span>'.format(
                        token.content, token.error_message)
        elif self.errors_mode == Converter.ERRORS_TESTING:
            error_func = lambda token: u"<<ERROR>>"
        else:
            error_func = lambda token: u""

        class HTMLConverterState(object):
            def __init__(self):
                self.any_content_yet = False
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
            state.any_content_yet = True
            if not self.paragraphs_disabled and not state.is_in_paragraph:
                indent = state.indent_next and not state.all_no_indent

                css_class = ""
                css_style = ""
                parskip = state.lengths_html['\\parskip']
                if parskip is not None:
                    # It seems to be the top, not the bottom that's affected.
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
                add_content_par(
                        self.get_latex_html__func(element, token.force_inline))
            elif isinstance(token, TokenText):
                add_content_par(xss.escape(token.text).replace('~', '&nbsp;'))
            elif isinstance(token, TokenSimpleWhitespace):
                if self.state.any_content_yet:
                    output.append(" ")  # Single whitespace is enough.
            elif isinstance(token, TokenMultilineWhitespace):
                if self.paragraphs_disabled:
                    output.append("<br>")
                elif self.state.any_content_yet:
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
                add_content_par(self.process_bb(token, TYPE_HTML))
            else:
                raise NotImplementedError(repr(token))
        return self.finalize_output(output, error_func)

    def convert_to_latex(self):
        output = []
        if self.errors_mode == Converter.ERRORS_ENABLED:
            error_func = lambda token: "\\textbf{%s} %s" % \
                    (token.error_message, token.content)
        elif self.errors_mode == Converter.ERRORS_TESTING:
            error_func = lambda token: u"<<ERROR>>"
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
