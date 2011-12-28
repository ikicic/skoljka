from django.conf import settings
import os, sys, hashlib

export_header = r'''
\documentclass[12pt,a4paper,oneside,final]{article}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[croatian]{babel}
\usepackage[centertags,intlimits,namelimits,sumlimits]{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}
\usepackage{enumitem}

\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}

\renewcommand{\ge}{\geqslant}
\renewcommand{\geq}{\geqslant}
\renewcommand{\le}{\leqslant}
\renewcommand{\leq}{\leqslant}
\renewcommand{\angle}{\sphericalangle}

\DeclareMathOperator{\tg}{tg}
\DeclareMathOperator{\ctg}{ctg}


\begin{document}
'''

# use %(title)s to get task title, and %(content)s to get problem statement
export_task = u'''
    %(title)s
    
    %(content)s
'''

export_footer = r'''
\end{document}
'''

tex_preamble = r'''
\documentclass{article}
\usepackage{amsmath}
\usepackage{amsthm}
\usepackage{amssymb}
\pagestyle{empty}
\begin{document}
'''

# TODO: enable client-side caching
def generate_png(eq, format):
    eq_hash = hashlib.md5(eq+format).hexdigest()
    filename = os.path.normpath(os.path.join(settings.PROJECT_ROOT, 'mathcontent/static/math/' + eq_hash))

    if os.path.exists(filename + '.png'):
        return eq_hash    

    f = open(filename + '.tex', 'w')
    f.write(tex_preamble)
    f.write(format % eq)
    f.write('\end{document}')
    f.close()
    
    # TODO: handle errors
    # TODO: disable logs
    os.system('latex -output-directory=%s -interaction=batchmode %s.tex' % (os.path.dirname(filename), filename) )
    # TODO: handle errors and test quality
    cmd = "dvipng -bg Transparent --gamma 1.5 -D 120 -T tight --strict -o %s.png %s" % (filename, filename)
    os.system(cmd)
    
    os.remove(filename + '.tex')
    os.remove(filename + '.log')
    os.remove(filename + '.aux')
    os.remove(filename + '.dvi')
    
    return eq_hash
