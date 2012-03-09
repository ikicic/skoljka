from skoljka.utils import xss
from mathcontent.latex import generate_png

inline_format = "$%s$ \n \\newpage \n"
block_format = "\\[\n%s \n\\] \n \\newpage \n"

img_url_path = '/media/math/'

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

def convert_to_html(T): # XSS danger!!! Be careful
    i = 0
    n = len(T)
    out = []
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
            if inline:
                hash, depth = generate_png(latex, inline_format)
                img = '<img src="%s%s.png" alt="%s" class="latex" style="vertical-align:%dpx">' % (img_url_path, hash, latex_escaped, -depth)
            else:
                hash, depth = generate_png(latex, block_format)
                img = '<img src="%s%s.png" alt="%s" class="latex_center">' % (img_url_path, hash, latex_escaped)

            out.append(img)
        else:
            out.append(html_escape_table.get(T[i], T[i]))
            i += 1

    return u''.join(out)


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
