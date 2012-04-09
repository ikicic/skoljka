from skoljka.utils import xss

from mathcontent import ERROR_DEPTH_VALUE
from mathcontent.latex import generate_png
from mathcontent.latex import generate_svg

inline_format = "$%s$"
block_format = "\\[%s\\]"
advanced_format = "%s"

img_url_path = '/media/m/'

reserved = {
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

tag_open = {
    'b': '<b>',
    'i': '<i>',
    'quote': '<div class="quote">',

# img accepts attachment attribute, index of attachment to use as a src (1-based)
    'img': '<img alt="Attachment image"%(extra)s>',
}

# automatically converted attributes as %(extra)s
tag_attrs = {
    'img': ('width', 'height'),
}

# tags without a close tag should have None value (or not be defined at all)
tag_close = {
    'b': '</b>',
    'i': '</i>',
    'quote': '</div>',
    'img': None,
}


def parse_bb_code(S):
    """
        Split tag name and attributes.
        Returns tuple (name, attrs), where attrs is a dictionary.
        
        Note:
            Doesn't support spaces and = symbol in attribute values!
        
        Example:
            S = 'img attachment=2 width=100px'
            
            name = u'img'
            attrs = {u'attachment': u'2', u'width': u'100px'}
    """
    
    # is there any shortcut for this in Python 2.7?
    tmp = S.split(' ')
    name = tmp[0]
    attrs = tmp[1:]
    
    attrs = dict([x.split('=') for x in attrs])
    
    return name, attrs


# TODO: change i to iterator
def convert_to_html(T, content=None): # XSS danger!!! Be careful
    """
        Converts MathContent format to HTML
        
        To support features like [img], it must be called with a 
        a content instance.
    """

    i = 0
    n = len(T)
    out = []
    tag_stack = []
    while i < n:
        if T[i] == '\\':
            # parse \$ and similar
            if i + 1 < n:
                out.append(T[i + 1])
            i += 2
        elif T[i:i+2] == '\r\n':
            out.append('<br>')
            i += 2
        elif T[i] == '\r' or T[i] == '\n':
            out.append('<br>')
            i += 1
        elif T[i] == '[':   # [quote]  [/quote] and similar
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
                # TODO: output original message part on any error
                try:
                    tag, attrs = parse_bb_code(T[i+1:end])
                except:
                    # if bb code not valid (or if not bb code at all), output original text
                    out.append(T[i+1:end])
                    
                if tag[0] == '/':
                    tag = tag[1:]
                    if not tag_stack or tag_stack[-1] != tag:
                        out.append('{{ Poredak otvorenih i zatvorenih tagova nije valjan. }}')
                    else:
                        out.append(tag_close[tag_stack.pop()])
                elif tag not in tag_open:
                    out.append('{{ Nevaljan tag &quot;%s&quot; }}' % xss.escape(tag))
                else:
                    # ask for close tag if there should be one
                    if tag_close.get(tag, None) is not None:
                        tag_stack.append(tag)
                    open = tag_open[tag]

                    # process attributes
                    extra = ''
                    if tag in tag_attrs:
                        for key, value in attrs.iteritems():
                            if key in tag_attrs[tag]:
                                extra += ' %s="%s"' % (key, xss.escape(attrs[key]))
                    
                    if tag == 'img':
                        if not content:
                            open = u'{{ Slika nije dostupna u pregledu }}'
                        elif 'attachment' not in attrs:
                            open = u'{{ Nedostaje "attachment" atribut }}'
                        else:
                            try:
                                k = int(attrs['attachment']) - 1
                                file = content.attachments.order_by('id')[k]
                                extra += ' src="%s"' % xss.escape(file.get_url())
                            except:
                                open = u'{{ Greška pri preuzimanju img datoteke. (Nevaljan broj?) }}'
                        
                    open %= {'extra': extra}
                    out.append(open)
                i = end + 1
        elif T[i] == '$':
            # parse $  $, $$  $$ and $$$  $$$
            cnt = 0
            while i < n and T[i] == '$':
                cnt += 1
                i += 1
                
            inline = cnt == 1
            if cnt == 1:
                format = inline_format
            elif cnt == 2:
                format = block_format
            else:
                format = advanced_format

            # this should work for all weird cases with \\ and \$
            latex = []
            while i < n:
                if T[i:i+2] == '\\$' or T[i:i+2] == '\\\\':
                    latex.append(T[i:i+2])
                    i += 2
                elif cnt <= 2 and T[i] == '$' or cnt == 3 and T[i:i+2] == '$$':
                # this could be also written more strictly as
                # elif T[i:i+cnt] == '$' * cnt:
                    break;
                else:
                    latex.append(T[i])
                    i += 1
            
            # don't care how many $ are there, just skip them
            while i < n and T[i] == '$':
                i += 1

            latex = u''.join(latex)
            latex_escaped = xss.escape(latex)
            
            # FIXME: don't save error message to depth
            hash, depth = generate_png(latex, format)
            if depth == ERROR_DEPTH_VALUE:
                out.append('{{ INVALID LATEX }}')
            else:
                url = '%s%s/%s/%s/%s.png' % (img_url_path, hash[0], hash[1], hash[2], hash)
                if inline:
                    img = '<img src="%s" alt="%s" class="latex" style="vertical-align:%dpx">' % (url, latex_escaped, -depth)
                else:
                    img = '<img src="%s" alt="%s" class="latex_center">' % (url, latex_escaped)

                out.append(img)

            # FIXME: don't save error message to depth
            # hash, depth = generate_svg(latex, format, inline)
            hash, depth = 'aaaaaaaaaaaaa', 0
            if depth == ERROR_DEPTH_VALUE:
                out.append('{{ INVALID LATEX }}')
            else:
                url = '%s%s/%s/%s/%s.svg' % (img_url_path, hash[0], hash[1], hash[2], hash)
                if inline:
                    obj = '<object data="%s" type="image/svg+xml" alt="%s" class="latex" style="vertical-align:%fpt"></object>' % (url, latex_escaped, -depth)
                else:
                    obj = '<object data="%s" type="image/svg+xml" alt="%s" class="latex_center"></object>' % (url, latex_escaped)

                # out.append(obj)

        else:
            out.append(html_escape_table.get(T[i], T[i]))
            i += 1

    if tag_stack:
        out.append('{{ Neki tagovi nisu zatvoreni }}')
        while tag_stack:
            out.append(tag_close[tag_stack.pop()])
    return u''.join(out)

# TODO: [img][/img] support
# TODO: change i to iterator
# TODO: performace test
def convert_to_latex(T):
    """
        Converts MathContent Format to LaTeX
        
        Replaces # % ^ & _ { } ~ \
        with \# \% \textasciicircum{} \& \_ \{ \} \~{} \textbackslash{},
        but keeps \$ as \$, because $ is a special char anyway
    """

    out = []
    
    n = len(T)
    i = 0
    while i < n:
        if T[i] == '\\':
            if i + 1 < n:
                out.append(T[i:i+2])
            # else: report error
            i += 2
        elif T[i] == '$':
            # copy string between $ $ or $$ $$
            while i < n and T[i] == '$':
                out.append('$')
                i += 1
            while i < n:
                if T[i] == '\\':
                    if i + 1 < n:
                        out.append(T[i:i+2])
                    # else: report error
                    i += 2;
                elif T[i] == '$':
                    break;
                else:
                    out.append(T[i])
                    i += 1
            while i < n and T[i] == '$':
                out.append('$')
                i += 1                        
        else:
            out.append(reserved.get(T[i], T[i]))
            i += 1

    return u''.join(out)
