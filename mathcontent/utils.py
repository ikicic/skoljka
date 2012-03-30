from skoljka.utils import xss

from mathcontent import ERROR_DEPTH_VALUE
from mathcontent.latex import generate_png

inline_format = "$%s$ \n \\newpage \n"
block_format = "\\[\n%s \n\\] \n \\newpage \n"

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
    'quote': '<div class="quote">',
}

tag_close = {
    'quote': '</div>',
}

# TODO: change i to iterator
def convert_to_html(T): # XSS danger!!! Be careful
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
            else:
                # TODO: output original message part on any error
                tag = T[i+1:end]
                if tag[0] == '/':
                    tag = tag[1:]
                    if not tag_stack or tag_stack[-1] != tag:
                        out.append('{{ Poredak otvorenih i zatvorenih tagova nije valjan. }}')
                    else:
                        out.append(tag_close[tag_stack.pop()])
                elif tag not in tag_open:
                    out.append('{{ Nevaljan tag &quot;%s&quot; }}' % xss.escape(tag))
                else:
                    tag_stack.append(tag)
                    out.append(tag_open[tag])
                i = end + 1
        elif T[i] == '$':
            # parse $  $ and $$  $$
            i += 1
            if i < n and T[i] == '$':
                inline = False
                i += 1
            else:
                inline = True

            # this should work for all weird cases with \\ and \$
            latex = []
            while i < n:
                if T[i:i+2] == '\\$' or T[i:i+2] == '\\\\':
                    latex.append(T[i:i+2])
                    i += 2
                elif T[i] == '$':
                    break;
                else:
                    latex.append(T[i])
                    i += 1
            
            # don't care how many $ are there, just skip them
            while i < n and T[i] == '$':
                i += 1

            latex = u''.join(latex)
            latex_escaped = xss.escape(latex)
            
            hash, depth = generate_png(latex, inline_format if inline else block_format)
            if depth == ERROR_DEPTH_VALUE:
                out.append('{{ INVALID LATEX }}')
            else:
                url = '%s%s/%s/%s/%s.png' % (img_url_path, hash[0], hash[1], hash[2], hash)
                if inline:
                    img = '<img src="%s" alt="%s" class="latex" style="vertical-align:%dpx">' % (url, latex_escaped, -depth)
                else:
                    img = '<img src="%s" alt="%s" class="latex_center">' % (url, latex_escaped)

                out.append(img)
        else:
            out.append(html_escape_table.get(T[i], T[i]))
            i += 1

    if tag_stack:
        out.append('{{ Neki tagovi nisu zatvoreni }}')
        while tag_stack:
            out.append(tag_close[tag_stack.pop()])
    return u''.join(out)

# TODO: change i to iterator
# TODO: performace test
def convert_to_latex(T):
    # replaces # % ^ & _ { } ~ \
    # with \# \% \textasciicircum{} \& \_ \{ \} \~{} \textbackslash{}
    # keeps \$ as \$, because $ is a special char anyway


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
