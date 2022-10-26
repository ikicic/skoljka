# coding=utf-8

from skoljka.utils import xss

from skoljka.mathcontent.models import ERROR_DEPTH_VALUE, IMG_URL_PATH, \
        TYPE_HTML, TYPE_LATEX
from skoljka.mathcontent.latex import get_or_generate_png

# Prepend this to the text to use this converter.
VERSION_MARKER = '%V0'

inline_format = "$%s$"
block_format = "\\[%s\\]"
advanced_format = "%s"

latex_escape_table = {
    '#': '\\#',
    '%': '\\%',
    '^': '\\textasciicircum{}',
    '&': '\\&',
    '_': '\\_',
    '{': '\\{',
    '}': '\\}',
    '~': '\\~{}',
    '\\': '\\textbackslash{}',
}

html_escape_table = {
    '&': '&amp;',   # this one must be the first
    '"': '&quot;',
    "'": '&apos;',
    '>': '&gt;',
    '<': '&lt;',
}

# (HTML, LaTeX)
tag_open = {
    'b': ('<b>', '\\textbf{'),
    'i': ('<i>', '\\emph{'),
    's': ('<s>', '\\sout{'),
    'u': ('<u>', '\\uline{'),
    'quote': ('<div class="quote">', ''),

# img accepts attachment attribute, index of attachment to use as a src (1-based)
    'img': ('<img alt="Attachment image"%(extra)s>', '\\includegraphics%(extra)s'),
    'url': ('<a href="%(url)s" rel="nofollow">', '%(url)s'),   # TODO: LaTeX links
}

# automatically converted attributes as %(extra)s
tag_attrs = {
    'img': ('width', 'height'),
}
# img accepts attachment attribute, index of attachment to use as a src (1-based)

# (HTML, LaTeX)
# tags without a close tag should have value None (or not be defined at all)
tag_close = {
    'b': ('</b>', '}'),
    'i': ('</i>', '}'),
    's': ('</s>', '}'),
    'u': ('</u>', '}'),
    'quote': ('</div>', ''),
    'img': None,
    'url': ('</a>', ''),
}


def parse_bb_code(S):
    """
        Split tag name and attributes.
        Returns tuple (name, attrs), where attrs is a dictionary.

        Note:
            Doesn't support spaces in attribute values!

        Example:
            S = 'img attachment=2 width=100px'

            name = u'img'
            attrs = {u'attachment': u'2', u'width': u'100px'}
    """

    # is there any shortcut for this in Python 2.7?
    tmp = S.split(' ')
    name = tmp[0]
    attrs = tmp[1:]

    attrs = dict([x.split('=', 2) for x in attrs])

    # Additionally, check if the name is an attribute (e.g. [url=(...)][/url])
    if '=' in name:
        name, value = S.split('=', 1)
        attrs[name] = value

    return name, attrs


def _convert(type, T, handle_latex_func, escape_table, attachments=None,
        attachments_path=None): # XSS danger!!! Be careful
    """
        Converts MathContent format to HTML (type 0) or LaTeX (type 1)

        To support features like [img], it must be called with a
        list of Attachment instances.
    """

    # force strip
    T = T.strip()

    if type == TYPE_HTML:
        newline = '<br>'
    else:
        newline = '\n'

    i = 0
    n = len(T)
    out = []
    tag_stack = []
    while i < n:
        if T[i] == '\\':
            # parse \$ and similar
            if i + 1 < n:
                out.append(escape_table.get(T[i + 1], T[i + 1]))
            i += 2
        elif T[i:i+2] == '\r\n':
            out.append(newline)
            i += 2
        elif T[i] == '\r' or T[i] == '\n':
            out.append(newline)
            i += 1
        elif T[i] == '[':   # BBCode
            # TODO: [url] can't contain ]
            end = T.find(']', i)
            if end == -1:
                out.append('[')     # no error messages for now
                i += 1
            elif end == i + 1:
                out.append('[]')
                i += 2
            elif end == i + 2 and T[i+1] == '/':
                out.append('[/]')
                i += 3
            else: # non empty tag
                # here we make difference between TYPE_HTML and TYPE_LATEX
                # TYPE_HTML = first element of tag tuple
                # TYPE_LATEX = second element of tag tuple

                try:
                    tag, attrs = parse_bb_code(T[i+1:end])
                except:
                    # if bb code not valid (or if not bb code at all), output original text
                    out.append('[%s]' % T[i+1:end])
                    i = end + 1
                    continue

                if tag[0] == '/':
                    tag = tag[1:]
                    if not tag_stack or tag_stack[-1] != tag:
                        out.append('{{ Poredak otvorenih i zatvorenih tagova nije valjan. }}')
                    else:
                        out.append(tag_close[tag_stack.pop()][type])
                elif tag not in tag_open:
                    out.append('{{ Nevaljan tag &quot;%s&quot; }}' % xss.escape(tag))
                else:
                    # ask for close tag if there should be one
                    if tag_close.get(tag, None) is not None:
                        tag_stack.append(tag)

                    open = tag_open[tag][type]

                    # process attributes
                    # WARNING: currently HTML and LaTeX use same attribute names and formats!
                    extra = ''
                    if tag in tag_attrs:
                        for key, value in attrs.iteritems():
                            if key in tag_attrs[tag]:
                                if type == TYPE_HTML:
                                    extra += ' %s="%s"' % (key, xss.escape(attrs[key]))
                                else:
                                    extra += ',%s=%s' % (key, xss.escape(attrs[key]))

                    if tag == 'img':
                        if attachments is None:
                            open = u'{{ Slika nije dostupna u pregledu }}'
                        elif 'attachment' not in attrs:
                            open = u'{{ Nedostaje "attachment" atribut }}'
                        else:
                            try:
                                k = int(attrs['attachment']) - 1
                                file = attachments[k]
                                if type == TYPE_HTML:
                                    extra += ' src="%s"' % xss.escape(file.get_url())
                                else: # type == TYPE_LATEX
                                    if attachments_path:
                                        filename = '{}/{}/{}'.format(
                                            attachments_path, k, file.get_filename())
                                    else:
                                        filename = file.get_full_path_and_filename()
                                    extra = '[%s]{%s}' % (extra[1:], filename)
                            except IndexError:
                                open = u'{{ Greška pri preuzimanju img datoteke. (Nevaljan broj?) }}'
                    elif tag == 'url':
                        # TODO: show icon for external URLs
                        # Manually get the URL if not given.
                        if 'url' not in attrs:
                            url_end = T.find('[/url]', i)
                            if url_end == -1:
                                open = u'{{ Nedostaje [/url] }}'
                            else:
                                attrs['url'] = T[i + 5:url_end]
                        attrs['url'] = xss.escape(attrs.get('url', ''))

                    attrs.update({'extra': extra})
                    open %= attrs
                    out.append(open)
                i = end + 1
        elif T[i] == '$':
            # parse $  $, $$  $$ and $$$  $$$
            cnt = 0
            while i < n and T[i] == '$':
                cnt += 1
                i += 1
            if cnt > 3:
                cnt = 3

            # this should cover all weird cases with \\ and \$
            latex = []
            while i < n:
                if T[i:i+2] == '\\$' or T[i:i+2] == '\\\\':
                    latex.append(T[i:i+2])
                    i += 2
                elif cnt <= 2 and T[i] == '$' or cnt == 3 and T[i:i+2] == '$$':
                # It is possible to use $ ... $ inside inside of $$$ ... $$$.
                # This could be also written more strictly as
                # elif T[i:i+cnt] == '$' * cnt:
                    break;
                else:
                    latex.append(T[i])
                    i += 1

            # don't care how many $ are there, just skip them
            while i < n and T[i] == '$':
                i += 1

            latex = u''.join(latex)

            out.append(handle_latex_func(cnt, latex))
        else:
            out.append(escape_table.get(T[i], T[i]))
            i += 1

    if tag_stack:
        out.append('{{ Neki tagovi nisu zatvoreni }}')
        while tag_stack:
            out.append(tag_close[tag_stack.pop()][type])
    return u''.join(out)


def _handle_latex_html(cnt, latex):
    """Generate LaTeX PNGs and outputs <img> tag."""
    latex_escaped = xss.escape(latex)

    inline = cnt == 1
    if cnt == 1:
        format = inline_format
    elif cnt == 2:
        format = block_format
    else:
        format = advanced_format

    # FIXME: don't save error message to depth
    latex_element = get_or_generate_png(format, latex)
    if latex_element.depth == ERROR_DEPTH_VALUE:
        return '{{ INVALID LATEX }}'
    else:
        hash = latex_element.hash
        url = '%s%s/%s/%s/%s.png' % (IMG_URL_PATH, hash[0], hash[1], hash[2], hash)
        if inline:
            img = '<img src="%s" alt="%s" class="latex" style="vertical-align:%dpx">' % (url, latex_escaped, -latex_element.depth)
        else:
            img = '<img src="%s" alt="%s" class="latex-center">' % (url, latex_escaped)

        return img

    # # FIXME: don't save error message to depth
    # hash, depth = generate_svg(latex, format, inline)
    # if depth == ERROR_DEPTH_VALUE:
    #     out.append('{{ INVALID LATEX }}')
    # else:
    #     url = '%s%s/%s/%s/%s.svg' % (IMG_URL_PATH, hash[0], hash[1], hash[2], hash)
    #     if inline:
    #         obj = '<object data="%s" type="image/svg+xml" alt="%s" class="latex" style="vertical-align:%fpt"></object>' % (url, latex_escaped, -depth)
    #     else:
    #         obj = '<object data="%s" type="image/svg+xml" alt="%s" class="latex-center"></object>' % (url, latex_escaped)

    #     # out.append(obj)


def _handle_latex_latex(cnt, text):
    """Convert dollar formatting to the correct LaTeX formatting."""

    if cnt == 1:
        return u'$%s$' % text
    if cnt == 2:
        return u'\\[%s\\]' % text
    # $$$ uses no formatting
    return text


def convert_to_html(T, attachments=None):
    """Convert MathContent format to HTML.

    Handles BBCode tags, converts LaTeX to images and escapes special chars."""
    return _convert(TYPE_HTML, T, _handle_latex_html, html_escape_table,
            attachments=attachments)


def convert_to_latex(T, attachments=None, attachments_path=None):
    """Convert MathContent Format to LaTeX.

    Replaces # % ^ & _ { } ~ \\
    with \# \% \\textasciicircum{} \& \_ \{ \} \~{} \\textbackslash{},
    but keeps \$ as \$, because $ is a special char anyway.

    Handles BBCode [i], [b] etc.
    """
    return _convert(TYPE_LATEX, T, _handle_latex_latex, latex_escape_table,
        attachments=attachments, attachments_path=attachments_path)

def convert(type, text, attachments=None, attachments_path=None):
    """Convert given text to the given type in the context of the given
    attachments."""
    if type == TYPE_HTML:
        return convert_to_html(text, attachments=attachments)
    if type == TYPE_LATEX:
        return convert_to_latex(text, attachments=attachments,
                attachments_path=attachments_path)
