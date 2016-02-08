from django.utils.translation import ugettext as _

from skoljka.libs import xss

from mathcontent.models import ERROR_DEPTH_VALUE, IMG_URL_PATH, TYPE_HTML, \
        TYPE_LATEX
from mathcontent.latex import generate_png, generate_svg

# Prepend this to the text to use this converter.
VERSION_MARKER = '%VERSION1'

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
# General helper functions.
########################################################
def float_to_str_pretty(val):
    return "{}".format(val).rstrip('0').rstrip('.')


def is_between(c, a, b):
    """Check if the unicode value of char c is between values of a and b."""
    u = unichr(c)
    return unichr(a) <= u and u <= unichr(b)


def startswith_ex(T, start, string):
    """As startswith, but with a specified start."""
    return T[start:start + len(string)] == string


def warning(msg):
    return "{{ " + msg + " }}"


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
            raise BBCodeError(_("Invalid format:") + " " + val)
        result[name.strip()] = val.strip()
    return result


########################################################
# Exceptions
########################################################
# TODO: Handle exceptions.
class BBCodeError(Exception):
    pass


class ParseError(Exception):
    pass


class CriticalError(ParseError):
    def __init__(self, converter, index, msg):
        self.converter = converter
        self.index = index
        super(CriticalError, self).__init__(msg)


class TooManyParseErrors(ParseError):
    pass

########################################################
# Tag/command-specific helper functions
########################################################

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
        elif name != 'attachment':
            raise ParseError(_("Unexpected attribute:") + " " + name)
    return (' width="{}"'.format(width) if width else '') + \
           (' height="{}"'.format(height) if height else '')


def img_params_to_latex(params):
    out = {}
    scale = []
    for name, value in params.iteritems():
        name = name.lower()
        value = value.strip()
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
        elif name != 'attachment':
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
class Command(object):
    def __init__(self, argc, parse_content):
        self.parse_content = parse_content
        self.argc = argc



class LatexContainer(Command):
    def __init__(self, html_open, html_close, argc=1, parse_content=True):
        super(LatexContainer, self).__init__(
                argc=argc, parse_content=parse_content)
        self.html_open = html_open
        self.html_close = html_close

    def contribute(self, converter, name, content, params):
        if converter.type == TYPE_HTML:
            return self.html_open + content + self.html_close
        if converter.type == TYPE_LATEX:
            assert self.argc <= 1
            if self.argc == 0:
                return '\\' + name
            else:
                return '\\' + name + '{' + content + '}'



class LatexHref(Command):
    def __init__(self):
        super(LatexHref, self).__init__(argc=2, parse_content=False)

    def contribute(self, converter, name, contents, params):
        url, desc = contents
        if converter.type == TYPE_HTML:
            return u'<a href="{}" rel="nofollow">{}</a>'.format(
                    xss.escape(url), xss.escape(desc))
        elif converter.type == TYPE_LATEX:
            return u'\\href{%s}{%s}' % (latex_escape(url), latex_escape(desc))



class LatexIncludeGraphics(Command):
    def __init__(self):
        super(LatexIncludeGraphics, self).__init__(argc=1, parse_content=False)

    def contribute(self, converter, name, content, params):
        if converter.attachments is None:
            return warning(_("Attachments not shown in a preview."))
        filename = content.strip()
        try:
            attachment = converter.attachments_dict[filename]
        except KeyError:
            raise BBCodeError(_("Attachment not found:") + " " + content.strip())
        if converter.type == TYPE_HTML:
            params = parse_latex_params(params)
            return u'<img src="{}" alt="Attachment {}" class="latex"{}>'.format(
                    xss.escape(attachment.get_url()),
                    xss.escape(filename),
                    img_params_to_html(params))
        if converter.type == TYPE_LATEX:
            if params:
                params = '[' + params + ']'
            return u'\\includegraphics%s{%s}' % (params, content)



class LatexSpecialSymbol(LatexContainer):
    def __init__(self, html, argc=1):
        super(LatexSpecialSymbol, self).__init__(html, '', argc=argc)



class LatexURL(Command):
    def __init__(self):
        super(LatexURL, self).__init__(argc=1, parse_content=False)

    def contribute(self, converter, name, content, params):
        if converter.type == TYPE_HTML:
            # For example, in \url{...} character sequence "\}" is not
            # allowed, and % is not treated as a comment. (!)
            url = xss.escape(content)
            return u'<a href="{}" rel="nofollow">{}</a>'.format(url, url)
        elif converter.type == TYPE_LATEX:
            return u'\\url{' + content + '}'



class LatexBeginCommand(Command):
    def __init__(self, html_open, html_close):
        super(LatexBeginCommand, self).__init__(argc=1, parse_content=True)
        self.html_open = html_open
        self.html_close = html_close

    def contribute(self, converter, name, content, params):
        if converter.type == TYPE_HTML:
            # TODO: params
            return self.html_open + content + self.html_close
        if converter.type == TYPE_LATEX:
            if params:
                params = '[' + params + ']'
            return u'\\begin{%s}%s%s\\end{%s}' % (name, params, content, name)



class BBCodeTag(object):
    def __init__(self, has_close_tag=True, parse_content=True):
        self.has_close_tag = has_close_tag
        self.parse_content = parse_content



class BBCodeContainerWrapper(BBCodeTag):
    def __init__(self, latex_command):
        super(BBCodeContainerWrapper, self).__init__()

        # Convert to LaTeXContainer, which converts to HTML or LaTeX.
        self.latex_command = latex_command
        self.latex_container = latex_commands[latex_command]

    def contribute(self, converter, name, content, attributes):
        if len(attributes) != 1 or attributes[0][1] is not None:
            raise BBCodeError(_("Unexpected parameter(s)."))
        return self.latex_container.contribute(
                converter, self.latex_command, content, "")



class BBCodeContainer(BBCodeTag):
    def __init__(self, html_open, html_close, latex_open, latex_close):
        super(BBCodeContainer, self).__init__()
        self.html_open = html_open
        self.html_close = html_close
        self.latex_open = latex_open
        self.latex_close = latex_close

    def contribute(self, converter, name, content, attributes):
        if len(attributes) != 1 or attributes[0][1] is not None:
            raise BBCodeError(_("Unexpected parameter(s)."))
        if converter.type == TYPE_HTML:
            return self.html_open + content + self.html_close
        if converter.type == TYPE_LATEX:
            return self.latex_open + content + self.latex_close



class BBCodeImg(BBCodeTag):
    def __init__(self):
        super(BBCodeImg, self).__init__(has_close_tag=False)

    def contribute(self, converter, name, content, attributes):
        if converter.attachments is None:
            return warning(_("Attachments not shown in a preview."))
        if attributes[0][1] is not None:  # "img" attribute should be None.
            raise BBCodeError(_("Unexpected parameter:") + " " + "img")
        attributes = dict(attributes[1:])
        try:
            val = attributes['attachment'].strip()
            index = int(val) - 1
            attachment = converter.attachments[index]
        except KeyError:
            raise BBCodeError(_("Missing an attribute:") + " attachment")
        except ValueError:
            msg = _("Invalid value \"%(val)s\" for the attribute \"%(attr)s\".")
            raise BBCodeError(msg % {'val': val, 'attr': 'attachment'})
        except IndexError:
            raise BBCodeError(_("Unavailable attachment:") + " " + val)
        if converter.type == TYPE_HTML:
            return '<img src="{}" alt="Attachment #{}" class="latex"{}>'.format(
                    xss.escape(attachment.get_url()), val,
                    img_params_to_html(attributes))
        elif converter.type == TYPE_LATEX:
            return '\\includegraphics%s{%s}' % \
                    (img_params_to_latex(attributes), attachment.get_filename())



class BBCodeURL(BBCodeTag):
    def contribute(self, converter, name, content, attributes):
        url = attributes[0][1]
        if url is None:
            url = content
        if len(attributes) > 1:
            raise BBCodeError(_("Unexpected parameter(s)."))
        if converter.type == TYPE_HTML:
            return '<a href="{}" rel="nofollow">{}</a>'.format(
                    xss.escape(url), content)
        if converter.type == TYPE_LATEX:
            if attributes[0][1]:
                return '\\href{%s}{%s}' % (latex_escape(url), content)
            else:
                return '\\url{%s}' % latex_escape(url)



latex_commands = {
    '\\': LatexSpecialSymbol('<br>', argc=0),
    'emph': LatexContainer('<i>', '</i>'),
    'href': LatexHref(),
    'includegraphics': LatexIncludeGraphics(),
    'sout': LatexContainer('<s>', '</s>'),
    'textasciicircum': LatexSpecialSymbol('^'),
    'textasciitilde': LatexSpecialSymbol('~'),  # Not really.
    'textbackslash': LatexSpecialSymbol('\\'),
    'textbf': LatexContainer('<b>', '</b>'),
    'uline': LatexContainer('<u>', '</u>'),
    'url': LatexURL(),
    '~': LatexSpecialSymbol('~'),               # Not really.
}
latex_begin_commands = {
    'center': LatexBeginCommand('<div class="mc-center">', '</div>'),
}
bb_commands = {
    'b': BBCodeContainerWrapper('textbf'),
    'center': BBCodeContainer('<div class="mc-center">', '</div>',
                              '\\begin{center}', '\\end{center}'),
    'i': BBCodeContainerWrapper('emph'),
    'img': BBCodeImg(),
    # TODO: Quote for LaTeX.
    'quote': BBCodeContainer('<div class="mc-quote">', '</div>', '', ''),
    's': BBCodeContainerWrapper('sout'),
    'u': BBCodeContainerWrapper('uline'),
    'url': BBCodeURL(),
}


########################################################
# Converter
########################################################
class Converter(object):
    def __init__(self, type, T, attachments):
        # TODO: For the latex case, include the whitespace?
        self.T = T.strip()
        self.type = type
        self.attachments = attachments
        self.attachments_dict = {x.get_filename(): x for x in attachments or []}

        self.out = []
        self.bbcode = True
        self.error_cnt = 0
        self.end_pattern = None
        self.end_pattern_first_char = None

    def get_latex_picture(self, *args, **kwargs):
        # To be able to mock it.
        return get_latex_picture(*args, **kwargs)

    def is_end(self, i):
        if i >= len(self.T):
            return True
        return self.end_pattern_first_char == self.T[i] and \
                startswith_ex(self.T, i, self.end_pattern)

    def _add_error(self, i, msg):
        msg = u'<span class="mc-error">{} ' \
                u'<span class="mc-error-source">...{}...</span>'.format(
                        msg, self.T[max(i - 10, 0):i + 50])
        self.out.append(msg)
        self.error_cnt += 1
        if self.error_cnt >= 5:
            raise TooManyParseErrors()

    def handle_comment(self, i):
        k = i
        while not self.is_end(i) and self.T[i] != '\r' and self.T[i] != '\n':
            i += 1
        if self.T[i - 1:i + 1] == '\r\n':
            i += 1
        if type == TYPE_LATEX:
            self.out.append(self.T[k:i])  # Keep the comment!

        # Is this some special command?
        cmd = self.T[k + 1:i].strip()
        # NOT TESTED.
        if cmd == 'NOBBCODE':
            self.bbcode = False
        elif cmd == 'BBCODE':
            self.bbcode = True
        return i

    def handle_newline(self, i):
        line_ends = 0
        k = i
        # NOT TESTED.
        while not self.is_end(i) and self.T[i].isspace():
            if self.T[i] == '\r' or self.T[i] == '\n':
                line_ends += 1
            i += 2 if self.T[i:i + 2] == '\r\n' else 1
        if self.type == TYPE_LATEX:
            self.out.append(self.T[k:i])  # Keep the spaces!
        if self.type == TYPE_HTML and line_ends >= 2:
            self.out.append('<br>')
        return i

    def handle_whitespace(self, i):
        # NOT TESTED.
        k = self._skip_whitespace(i)
        if i != k and self.type == TYPE_LATEX:  # Not really necessary.
            self.out.append(T[i:k])
        return k

    def _skip_whitespace(self, i):
        while not self.is_end(i) and self.T[i].isspace():
            i += 1
        return i

    def handle_latex_params(self, i):
        """Parse [...] part after a command if it exists. Stops searching for
        [...] after the first blank line. Returns a pair (i, params), where
        params is a string. The final index points at the first character
        after ] if the [...] block exists, otherwise it just skips (and
        appends to self.out) whitespace."""
        line_ends = 0
        k = i
        while not self.is_end(i) and self.T[i].isspace():
            if self.T[i] == '\r' and self.T[i] == '\n':
                line_ends += 1
            i += 2 if self.T[i:i + 2] == '\r\n' else 1
        if line_ends > 1:
            if self.type == TYPE_LATEX:
                self.out.append(self.T[k:i])
            return i, ""
        if not self.is_end(i) and self.T[i] == '[':
            end = self._find_closing_bracket(i + 1, '[', ']')
            return end + 1, self.T[i + 1:end]
        return i, ""

    def _find_closing_bracket(self, i, left, right):
        """Find a matching bracket. Index i must skip the first open bracket.
        Treats open bracket between start and closing bracket as a syntax
        error."""
        end = self.T.find(right, i)
        if end == -1:
            raise CriticalError(self, i, _("Matching bracket not found."))
        if self.T.find(left, i, end - 1) != -1:
            raise CriticalError(self, i, _("Syntax error."))
        return end

    def _find_closing_curly_bracket_latex(self, i):
        """Find a matching closing bracket. Index i must skip the first open
        bracket. Treats \\} as a character }, not as the closing bracket.
        Return index points at the } bracket."""
        while not self.is_end(i) and self.T[i] != '}':
            # SPEED: Trie?
            for key, value in escape_table[TYPE_LATEX].iteritems():
                if self.T[i] == value[0] and startswith_ex(self.T, i, value):
                    # Skip the escaped character.
                    i += len(value) - 1
                    break
            i += 1
        if self.is_end(i):
            raise CriticalError(self, i, _("Matching bracket not found."))
        return i

    def handle_latex_begin_end_block(self, i):
        """Handle \\begin{...}[...] ... \\end{...}, where index i points at the
        first \\."""
        start = i

        # Parse \begin{...}
        i += len('\\begin{')
        end = self._find_closing_bracket(i + 1, '{', '}')
        name = self.T[i:end]

        # Parse [...]
        i = end + 1
        i, params = self.handle_latex_params(i)

        # Parse content.
        end_pattern = '\\end{' + name + '}'
        i, content = self.parse_until(i, '\\end{' + name + '}')

        if name in latex_begin_commands:
            cmd = latex_begin_commands[name]
            self.out.append(cmd.contribute(self, name, content, params))
        else:
            self._add_error(start, _("Unknown LaTeX environment."))
        return i + len(end_pattern)

    def handle_latex_command(self, i, name):
        cmd = latex_commands[name]
        start = i
        # TODO: Check how latex behaves in this case.
        i += 1 + len(name)
        i, params = self.handle_latex_params(i)

        # Latex wouldn't allow an empty line between "\somecommand" and "{}"(?).
        contents = []
        for k in range(cmd.argc):
            i = self.handle_whitespace(i)
            if not self.is_end(i) and self.T[i] == '{':
                if cmd.parse_content:
                    i, content = self.parse_until(i + 1, '}')
                else:
                    # No escaping performed here.
                    start = i + 1
                    i = self._find_closing_curly_bracket_latex(i)
                    content = self.T[start:i]
                i += 1
                contents.append(content)
            else:
                msg = _("Parameter #%d missing.") % (k + 1)
                msg += " " + _("Please put each argument in curly braces.")
                self._add_error(start, msg)
                contents.append("")


        # If argc == 1, send just the first
        if len(contents) == 0:
            content = ""
        elif len(contents) == 1:
            content = contents[0]
        else:
            content = contents
        self.out.append(cmd.contribute(self, name, content, params))
        return i

    def handle_latex_formula(self, i):
        """Handle $...$, $$...$$, \(...\), \[...\] and $$$ ... $$$."""
        prefix = ""
        dollars = 0
        if self.T[i] == '$':
            while not self.is_end(i) and self.T[i] == '$':
                dollars += 1
                i += 1
            if dollars >= 4:  # Special case
                prefix = self.get_latex_picture('$$%s$$', "") * (dollars // 4)
                dollars %= 4
                if dollars == 0:
                    self.out.append(prefix)
                    return i
            begin = '$' * dollars
            end = begin
        else:
            begin = self.T[i:i + 2]
            i += 2
            if begin == '\\(':
                end = '\\)'
            elif begin == '\\[':
                end = '\\]'
            else:
                raise Exception("Unreachable code. begin=" + begin)

        start = i
        # Here we don't care about self.end_pattern.
        while i < len(self.T) and not startswith_ex(self.T, i, end):
            i += 2 if self.T[i:i + 2] in ['\\\\', '\\$'] else 1
        if self.is_end(i) or not startswith_ex(self.T, i, end):
            raise ParseError(_("Missing the ending:") + " " + end)

        if begin == '$$$':
            format = '%s'
        elif begin == '$$':
            format = '\[%s\]'
        else:
            format = begin + '%s' + end
        latex = self.T[start:i]
        if self.type == TYPE_HTML:
            self.out.append(prefix + self.get_latex_picture(format, latex))
        elif self.type == TYPE_LATEX:
            self.out.append(prefix + format % latex)
        return i + len(end)


    def handle_backslash(self, i):
        if self.T[i:i + 2] in ['\(', '\[']:
            return self.handle_latex_formula(i)
        if startswith_ex(self.T, i + 1, "begin"):
            return self.handle_latex_begin_end_block(i)

        # SPEED: Trie?
        for key in latex_commands.iterkeys():
            if self.T[i + 1] == key[0] and startswith_ex(self.T, i + 1, key):
                return self.handle_latex_command(i, key)

        self._add_error(i, _("Unrecognized command:"))
        return i + 1

    def handle_string_literal(self, i, end_delimiters):
        """Parse a string of the format connected-text, 'multiple words' or
        "multiple words".

        Returns (i, string), where i points at the first character after the
        string. """
        if self.T[i] == '\'' or self.T[i] == '"':
            delimiter = self.T[start]
            out = []
            start = i
            while not self.is_end(i) and self.T[i] != delimiter:
                if self.T[i] == '\\' and not self.is_end(i + 1) and \
                        self.T[i + 1] == delimiter:
                    out.append(delimiter)
                    i += 2
                else:
                    out.append(self.T[i])
                    i += 1
            if self.is_end(i):
                raise CriticalError(
                        self, start, _("String missing the end delimiter."))
            return i + 1, u"".join(out)
        else:
            return self.handle_nonwhitespace_literal(i, end_delimiters)

    def handle_nonwhitespace_literal(self, i, end_delimiters):
        start = i
        while not self.is_end(i) and \
                not self.T[i].isspace() and \
                self.T[i] not in end_delimiters:
            i += 1
        return i, self.T[start:i]

    def handle_bbcode(self, i):
        """Parse BB Code tag. Index i points at the first open bracket [."""
        start = i
        attributes = []
        i += 1
        while True:
            i = self._skip_whitespace(i)
            if self.is_end(i) or self.T[i] == ']':
                break
            i, name = self.handle_nonwhitespace_literal(i, '=]')
            i = self._skip_whitespace(i)
            if self.is_end(i) or self.T[i] != '=':
                attributes.append((name, None))
                continue
            i, value = self.handle_string_literal(i + 1, '=]')
            attributes.append((name, value))

        try:
            if self.is_end(i) or self.T[i] != ']':
                raise ValueError()
            name = attributes[0][0]
            cmd = bb_commands[name]
        except (ValueError, IndexError, KeyError):
            if name not in bb_commands:
                return i, self.T[start:i]  # Silent error, return as is.

        content = ""
        try:
            i += 1  # Skip the closing bracket ].
            if not cmd.has_close_tag:
                return i, cmd.contribute(self, name, None, attributes)

            closing_tag = '[/' + name + ']'
            if cmd.parse_content:
                i, content = self.parse_until(i, closing_tag)
            else:
                # No escaping performed here.
                start = i
                i = self.T.find(i, closing_tag)
                if i == -1:
                    raise BBCodeError(_("Closing tag %s not found.") \
                            % closing_tag)
                content = self.T[start:i]
            i += len(closing_tag)
            return i, cmd.contribute(self, name, content, attributes)
        except BBCodeError as e:
            self._add_error(start, e.message)
            return i, content

    def parse_until(self, i, end_pattern):
        old = self.out, self.end_pattern, self.end_pattern_first_char

        self.out = []
        self.end_pattern = end_pattern
        self.end_pattern_first_char = end_pattern[0]
        # SPEED: self.out should be a list, because this is also O(N^2).
        start = i
        end, child_result = self.parse(i)
        if not startswith_ex(self.T, end, end_pattern):
            raise CriticalError(self, start, _("Matching \"%s\" not found.")
                    % end_pattern)

        self.out, self.end_pattern, self.end_pattern_first_char = old
        return end, child_result

    def parse(self, i):
        T = self.T
        out = self.out
        _escape_table = escape_table[self.type]

        while not self.is_end(i):
            if T[i] == '\r' or T[i] == '\n':
                i = self.handle_newline(i)
            elif T[i] == '%':
                i = self.handle_comment(i)
            elif T[i] == '\\':
                i = self.handle_backslash(i)
            elif T[i] == '[' and self.bbcode:
                i, content = self.handle_bbcode(i)
                out.append(content)
            elif T[i] == '$':
                i = self.handle_latex_formula(i)
            else:
                out.append(_escape_table.get(T[i], T[i]))
                i += 1

        return i, u"".join(out)

    def convert(self):  # XSS danger!!! Be careful
        """Converts MathContent format to HTML (type 0) or LaTeX (type 1)

        To support special tags like [img], it must be called with a
        content instance."""

        return self.parse(0)


def get_latex_picture(format, latex):
    """Generates LaTeX PNGs and outputs an <img> tag."""
    inline = format in ['$%s$', '\(%s\)']
    if format == '$$%s$$':
        format = '\[%s\]'
    latex_escaped = xss.escape(latex)

    # FIXME: don't save error message to depth
    hash, depth = generate_png(latex, format)
    if depth == ERROR_DEPTH_VALUE:
        # TODO: link to the log file.
        return '{{ INVALID LATEX }}'

    url = '%s%s/%s/%s/%s.png' % (IMG_URL_PATH, hash[0], hash[1], hash[2], hash)
    if inline:
        return '<img src="%s" alt="%s" class="latex" ' \
                'style="vertical-align:%dpx">' % (url, latex_escaped, -depth)
    else:
        return '<img src="%s" alt="%s" class="latex-center">' % \
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


def convert(type, text, attachments=None, attachments_path=None):
    """Convert given text to the given type in the context of the given
    attachments."""
    # TODO: attachments_path
    converter = Converter(type, text, attachments)
    try:
        i, output = converter.convert()
    except Exception as e:
        return _("Error converting the text:") + " " + e.message
    return output
