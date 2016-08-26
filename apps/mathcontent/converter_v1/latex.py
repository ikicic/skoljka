from django.utils.translation import ugettext as _

from skoljka.libs import xss

from mathcontent.converter_v1.basics import img_params_to_html, State, \
        COUNTER_EQUATION, COUNTER_FIGURE, test_eq, ParseError
from mathcontent.converter_v1.tokens import TokenError, TokenCommand, \
        TokenMath, TokenWarning, TOKEN_CLOSED_CURLY


class LatexValueError(Exception):
    pass

########################################################
# LaTeX Commands
########################################################

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


def _parse_latex_params(val):
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



class Command(object):
    def __init__(self, args_desc=""):
        """Args descriptor is a string of format <X><Y>...<Z>, where
        < > stands for [ ] or { }, and X for one of the following:
            P - parse ({} only)
            U - read as an URL ({} only)
            S - read until ']' ([] only).

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
        return test_eq(self, other)

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
            return tokenizer.read_until(']', [])

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



class _LatexEnvironmentReadUntil(object):
    def __init__(self):
        super(_LatexEnvironmentReadUntil, self).__init__()
        # Ignore everything after \end{...} until the end of line.
        # E.g. "LaTeX Warning: Characters dropped after `\end{verbatim}' (...)"
        self.ignore_until_eol = False



class LatexBegin(Command):
    # TODO: \begin[...]{equation} ... \end{equation}
    # TODO: \begin{equation} ... \end{equation}
    def __init__(self):
        # SIMPLIFICATION MARK: Ignoring comments, using U.
        super(LatexBegin, self).__init__(args_desc="{U}")

    def apply_command(self, tokenizer, name, args, whitespace):
        """Simply add itself to the current state."""
        environment_class = latex_environments.get(args[0])
        if not environment_class:
            latex = tokenizer.read_until('\\end{%s}' % args[0], [r'\\'])
            latex = '\\begin{%s}%s\\end{%s}' % (args[0], latex, args[0])
            return TokenMath('%s', latex)
            # return TokenError(_("Unknown LaTeX environment."), args[0])

        # Generate new LatexEnvironment instance.
        environment = environment_class()

        if isinstance(environment, _LatexEnvironmentReadUntil):
            end = '\\end{%s}' % args[0]
            latex = tokenizer.read_until_exact(end)
            tokenizer.state.add_token(TokenCommand(
                    name, 0, [args[0], environment, latex], whitespace))
            if environment.ignore_until_eol:
                try:
                    ignored = tokenizer.read_until_exact_any(['\r', '\n'])
                    tokenizer.K -= 1  # Do not skip the newline.
                except ParseError as e:
                    ignored = tokenizer.T[tokenizer.K:]
                    tokenizer.K = len(tokenizer.T)
                if ignored.strip():
                    tokenizer.state.add_token(TokenWarning(
                        _("Ignored the rest of the line after %s!") % end,
                        ignored))
            return

        # Pass environment as the arg.
        tokenizer.state.add_token(
                TokenCommand(name, 0, [args[0], environment], whitespace))
        tokenizer.push_state(State(break_condition='begin-' + args[0],
                environment=environment))

    def to_html(self, token, converter):
        environment = token.args[1]
        return environment.to_html(True, token, converter)

    def to_latex(self, token, converter):
        # Manually handle the _LatexEnvironmentReadUntil case.
        environment = token.args[1]
        result = super(LatexBegin, self).to_latex(token, converter)
        if isinstance(environment, _LatexEnvironmentReadUntil):
            return result + token.args[2] + '\\end{%s}' % token.args[0]
        return result



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
            return TokenError(_("Attachment not found:"), filename.strip())

        params = _parse_latex_params(token.args[0] or '')
        return u'<img src="{}" alt="Attachment {}" class="latex"{}>'.format(
                xss.escape(attachment.get_url()),
                xss.escape(filename),
                img_params_to_html(params.iteritems()))



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
        return test_eq(self, other)



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



class LatexEnvironmentVerbatim(LatexEnvironment, _LatexEnvironmentReadUntil):
    """Handles \\begin{verbatim}...\\end{verbatim} and the starred version."""
    def __init__(self):
        super(LatexEnvironmentVerbatim, self).__init__()
        self.ignore_until_eol = True

    def __repr__(self):
        return u'LatexEnvironmentVerbatim()'

    def to_html(self, begin, token, converter):
        env_name = token.args[0]
        content = token.args[2]
        if env_name == 'verbatim*':
            content = content.replace(' ', '&blank;')
        converter.state.is_in_paragraph = False
        converter.state.indent_next = False
        return '<pre class="mc-verbatim">{}</pre>'.format(xss.escape(content))


########################################################
# Default latex commands and environments
########################################################

latex_commands = {
    '%': LatexSpecialSymbol('%'),
    '-': LatexSpecialSymbol('&shy;'),  # Soft hyphen.
    'LaTeX': LatexInlineMathCommand('%s', '\\LaTeX'),
    'TeX': LatexInlineMathCommand('%s', '\\TeX'),
    '\\': LatexSpecialSymbol('<br>'),
    '{': LatexSpecialSymbol('{'),
    '}': LatexSpecialSymbol('}'),
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
    # 'equation': None, # LatexEnvironmentEquation(),
    'figure': LatexEnvironmentFigure,
    'flushleft': latex_environment_div_factory('mc-flushleft'),
    'flushright': latex_environment_div_factory('mc-flushright'),
    'verbatim': LatexEnvironmentVerbatim,
    'verbatim*': LatexEnvironmentVerbatim,
}
