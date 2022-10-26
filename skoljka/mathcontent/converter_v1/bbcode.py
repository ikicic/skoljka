from django.conf import settings
from django.utils.translation import ugettext as _

from skoljka.utils import xss

from skoljka.mathcontent.latex import latex_escape
from skoljka.mathcontent.converter_v1.basics import \
        img_parse_length, img_params_to_html
from skoljka.mathcontent.converter_v1.latex import \
        convert_tex_length_to_html, LatexValueError


class BBCodeException(Exception):
    pass


class BBUnexpectedParameters(BBCodeException):
    def __init__(self, param=None):
        if param is None:
            msg = _("Unexpected parameter(s).")
        else:
            msg = _("Unexpected parameter:") + " " + param
        super(BBUnexpectedParameters, self).__init__(msg)


# def bb_code_link(type, url, content):
#     """Output the <a...>...</a> tag or  \\url{...} or \\href{...}{...} command.
#
#     Content will be used as the url if the 'url' is empty.
#     """
#     if type == TYPE_HTML:
#         return u'<a href="{}" rel="nofollow">{}</a>'.format(
#                 xss.escape(url or content), content)
#     if type == TYPE_LATEX:
#         if url:
#             return u'\\href{%s}{%s}' % (latex_escape(url), content)
#         else:
#             return u'\\url{%s}' % latex_escape(content)

def _img_params_to_latex(params):
    out = {}
    scale = []
    for name, value in params:
        name = name.lower()
        value = (value or '').strip()
        if name in ['width', 'height']:
            if value[-1] == '%':
                try:
                    scale.append(str(float(value[:-1])))
                except ValueError:
                    raise ParseError(_("Expected a number."))
            else:
                out[name] = str(img_parse_length(value)) + 'pt'
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
    attrs = []
    while K < len(T) and T[K] != ']':
        while K < len(T) and T[K].isspace():
            K += 1  # Skip whitespace.

        # Read the variable name
        start = K
        while K < len(T) and (T[K].isalnum() or T[K] == '.'):
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

        if K == len(T):
            raise BBCodeException()

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
                attrs.append((attr_name, u"".join(value)))
            else:
                start = K
                while K < len(T) and T[K] not in ' \t\r\n]':
                    K += 1
                attrs.append((attr_name, T[start : K]))
        else:
            attrs.append((attr_name, None))
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
            if len(token.attrs) != 1 or token.attrs[0][1] is not None:
                raise BBUnexpectedParameters()
            return self.html_open
        return self.html_close

    def to_latex(self, token, converter):
        if token.is_open():
            if len(token.attrs) != 1 or token.attrs[0][1] is not None:
                raise BBUnexpectedParameters()
            return self.latex_open
        return self.latex_close



class BBCodeNoParseContainer(BBCodeContainer):
    def __init__(self, html_open, html_close, latex_open, latex_close):
        super(BBCodeNoParseContainer, self).__init__(
                html_open, html_close, latex_open, latex_close)

    def should_parse_content(self, token):
        return False

    def to_html(self, token, converter):
        if len(token.attrs) != 1 or token.attrs[0][1] is not None:
            raise BBUnexpectedParameters()
        return self.html_open + xss.escape(token.content) + self.html_close

    def to_latex(self, token, converter):
        if len(token.attrs) != 1 or token.attrs[0][1] is not None:
            raise BBUnexpectedParameters()
        return self.latex_open + token.content + self.latex_close



class BBCodeHide(BBCodeTag):
    def should_parse_content(self, token):
        return True

    def to_html(self, token, converter):
        if not token.is_open():
            return '</div></div>'
        if len(token.attrs) != 1:
            raise BBUnexpectedParameters()

        if token.attrs[0][1]:
            link_text = xss.escape(token.attrs[0][1])
        else:
            link_text = '+/-'
        return u'<div><a href="#" class="mc-hide-link">{}</a>' \
                u'<div class="mc-hide-content" style="display:none;">'.format(
                        link_text)

    def to_latex(self, token, converter):
        if not token.is_open():
            return '}'
        if len(token.attrs) != 1:
            raise BBUnexpectedParameters()

        if token.attrs[0][1]:
            return u'{\\color{gray}' + latex_escape(token.attrs[0][1]) + ': '
        else:
            return u'{\\color{gray}'



class BBCodeImg(BBCodeTag):
    def __init__(self):
        super(BBCodeImg, self).__init__(has_close_tag=False)

    def _check(self, token, converter):
        if converter.attachments is None:
            # return converter.warning(_("Attachments not shown in a preview."))
            # FIXME: Finish this...
            raise BBCodeException(_("Attachments not shown in a preview."))
        attrs_dict = dict(token.attrs)
        if attrs_dict['img'] is not None:  # "img" attribute should be None.
            raise BBUnexpectedParameters("img")
        try:
            val = attrs_dict['attachment'].strip()
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
                (_img_params_to_latex(token.attrs), attachment.get_filename())



class BBCodeLanguage(BBCodeTag):
    def should_parse_content(self, token):
        return True

    def to_html(self, token, converter):
        if not token.is_open():
            return '</div>'
        if token.attrs is None or len(token.attrs) != 1:
            raise BBUnexpectedParameters()
        lang = dict(token.attrs)['lang'];
        if lang is None:
            raise BBCodeException("Language not specified, use e.g. '[lang=en]...[/lang]'.")
        if not any(lang == lang_ for lang_, name in settings.LANGUAGES):
            raise BBCodeException(
                    "Unrecognized language code '{}'.".format(xss.escape(lang)))
        return u'<div class="lang lang-{}">'.format(lang)

    def to_latex(self, token, converter):
        if not token.is_open():
            return u'}'
        if len(token.attrs) != 1:
            raise BBUnexpectedParameters()
        return u'{'  # For now export all translations.


class BBCodePar(BBCodeTag):
    """[par <skip> <indent>], a shorthand for
        \\setlength{\\parskip}{<skip>}
        \\setlength{\\parindent}{<indent>}.
    """
    def __init__(self):
        super(BBCodePar, self).__init__(has_close_tag=False)

    def _check(self, token, converter, is_latex):
        if len(token.attrs) != 3:
            raise BBCodeException(_("Expected two attributes."))
        for k in range(3):
            if token.attrs[k][1] is not None:
                raise BBUnexpectedParameters(_("Unexpected attribute value:") +
                                             "%s=%s" % token.attrs[k])
        skip = token.attrs[1][0]
        indent = token.attrs[2][0]
        if skip == '0': skip = '0pt'
        if indent == '0': indent = '0pt'
        try:
            html_skip = convert_tex_length_to_html(skip)
            html_indent = convert_tex_length_to_html(indent)
        except LatexValueError:
            raise BBCodeException(_("Unexpected attribute value."))
        return (skip, indent) if is_latex else (html_skip, html_indent)

    def to_html(self, token, converter):
        skip, indent = self._check(token, converter, False)
        converter.state.lengths_html['\\parskip'] = skip
        converter.state.lengths_html['\\parindent'] = indent
        return u""

    def to_latex(self, token, converter):
        skip, indent = self._check(token, converter, True)
        return u"\\setlength{\\parskip}{%s}\n\\setlength{\\parindent}{%s}\n" % \
                (skip, indent)


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
        return dict(token.attrs)['url'] is not None

    def to_html(self, token, converter):
        if token.is_open():
            if len(token.attrs) > 1:
                raise BBUnexpectedParameters()
            if token.content is not None:
                return u'<a href="{}" rel="nofollow">{}</a>'.format(
                        xss.escape(token.content), xss.escape(token.content))
            return u'<a href="{}" rel="nofollow">'.format(
                    xss.escape(dict(token.attrs)['url']))
        return '</a>'

    def to_latex(self, token, converter):
        if token.is_open():
            if len(token.attrs) > 1:
                raise BBUnexpectedParameters()
            if token.content is not None:
                # [url]...[/url]
                return u'\\url{%s}' % latex_escape(token.content)
            # [url=...]
            return u'\\href{%s}{' % latex_escape(dict(token.attrs)['url'])
        # [/url]
        return '}'



bb_commands = {
    'b': BBCodeContainer('<b>', '</b>', '\\textbf{', '}'),
    'center': BBCodeContainer('<div class="mc-center">', '</div>',
                              '\\begin{center}', '\\end{center}'),
    'code': BBCodeContainer('<code>', '</code>', '\\texttt{', '}'),
    'hide': BBCodeHide(),
    'i': BBCodeContainer('<i>', '</i>', '\\textit{', '}'),
    'img': BBCodeImg(),
    'lang': BBCodeLanguage(),
    'par': BBCodePar(),
    'pre': BBCodeNoParseContainer(
            '<pre class="mc-verbatim">', '</pre>',
            '\\begin{verbatim}', '\\end{verbatim}\n'),  # The \n is important!
    # TODO: Quote for LaTeX.
    # TODO: Quote parameters.
    'quote': BBCodeContainer('<div class="mc-quote">', '</div>', '', ''),
    # 'ref': BBCodeRef(),
    # TODO: pre
    's': BBCodeContainer('<s>', '</s>', '\\sout{', '}'),
    'u': BBCodeContainer('<u>', '</u>', '\\uline{', '}'),
    'url': BBCodeURL(),
}

