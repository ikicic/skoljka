from django.conf import settings
import os, sys, hashlib, re

from mathcontent import ERROR_DEPTH_VALUE
from mathcontent.models import LatexElement

from skoljka.utils.timeout import run_command


# Obican .getstatusoutput ne radi na Windowimsa, ovo je zamjena
# Preuzeto s http://mail.python.org/pipermail/python-win32/2008-January/006606.html

mswindows = (sys.platform == "win32")
def getstatusoutput(cmd):
    """Return (status, output) of executing cmd in a shell."""

    if not mswindows:
        cmd = '{ ' + cmd + '; }'

    pipe = os.popen(cmd + ' 2>&1', 'r')
    text = pipe.read()
    status = pipe.close()

    if status is None:
        status = 0
    if text[-1:] == '\n':
        text = text[:-1]

    return status, text

def latex_full_filename(filename):
    return ('"%s%s"' if mswindows else '%s%s') % (settings.LATEX_BIN_DIR, filename)
    
export_header = u'''
\\documentclass[12pt,a4paper,oneside,final]{article}

\\usepackage[margin=2cm]{geometry}

\\usepackage[utf8]{inputenc}
\\usepackage[T1]{fontenc}
\\usepackage[croatian]{babel}
\\usepackage[centertags,intlimits,namelimits,sumlimits]{amsmath}
\\usepackage{amsfonts}
\\usepackage{amssymb}
\\usepackage{enumitem}

\\usepackage{fancyhdr}
\\fancypagestyle{empty}{
    \\fancyhf{}
    \\renewcommand{\\headrulewidth}{0pt}
    \\renewcommand{\\footrulewidth}{0pt}
}
\\fancypagestyle{plain}{
    \\fancyhf{}
    \\fancyfoot[R]{\\footnotesize\\bf\\thepage}
    \\fancyfoot[L]{\\footnotesize\\bf Školjka}
    \\renewcommand{\\headrulewidth}{0pt}
    \\renewcommand{\\footrulewidth}{0.5pt}
    \\renewcommand{\\footrule}{\\vskip-\\footrulewidth \\hrule width\\headwidth height\\footrulewidth}
}

\\setlength{\\parindent}{0pt}
\\setlength{\\parskip}{6pt}

\\renewcommand{\\ge}{\\geqslant}
\\renewcommand{\\geq}{\\geqslant}
\\renewcommand{\\le}{\\leqslant}
\\renewcommand{\\leq}{\\leqslant}
\\renewcommand{\\angle}{\\sphericalangle}

\\DeclareMathOperator{\\tg}{tg}
\\DeclareMathOperator{\\ctg}{ctg}

\\pagestyle{plain}


\\begin{document}
'''

# use %(title)s to get task title, and %(content)s to get problem statement
export_task = u'''
    \\section*{%(title)s}
    %(content)s
'''

export_footer = u'''
\\end{document}
'''

tex_preamble = r'''
\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath}
\usepackage{amsthm}
\usepackage{amssymb}
\usepackage[active]{preview}
\pagestyle{empty}
\begin{document}
\begin{preview}
'''

# TODO: enable client-side caching
# TODO: join depth queries
def generate_png(eq, format):
    eq_hash = hashlib.md5(eq+format).hexdigest()
    try:
        latex_element = LatexElement.objects.only("depth").get(hash=eq_hash)
        return eq_hash, latex_element.depth
    except:
        pass

    path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, 'm', eq_hash[0], eq_hash[1], eq_hash[2]))
    if not os.path.exists(path):
        os.makedirs(path)

    filename = os.path.normpath(os.path.join(path, eq_hash))

    
    f = open(filename + '.tex', 'w')
    f.write(tex_preamble)
    f.write(format % eq)
    f.write('\end{preview}\end{document}')
    f.close()
    
    # TODO: handle errors
    # TODO: disable logs
    cmd = '%s -output-directory=%s -interaction=batchmode %s.tex' % (latex_full_filename('latex'), os.path.dirname(filename), filename)
    error = run_command(cmd, timeout=5)
        
    if not error:
        # TODO: handle errors and test quality
        cmd = "%s -bg Transparent --gamma 1.5 -D 120 --depth* -T tight --strict -o %s.png %s" % (latex_full_filename('dvipng'), filename, filename)
        status, stdout = getstatusoutput(cmd)
    
    if not error and status == 0:
        depth_re = re.compile(r'\[\d+ depth=(-?\d+)\]')
        for line in stdout.splitlines():
            m = depth_re.match(line)
            if m:
                depth = int(m.group(1))
                break
    else: # error
        depth = ERROR_DEPTH_VALUE

    os.remove(filename + '.tex')
    os.remove(filename + '.log')
    os.remove(filename + '.aux')

    if not error and status == 0:
        os.remove(filename + '.dvi')

    latex_element = LatexElement(hash=eq_hash, text=eq, format=format, depth=depth)
    latex_element.save(force_insert=True)
    
    return eq_hash, depth
