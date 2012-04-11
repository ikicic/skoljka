from django.conf import settings
import os, sys, hashlib, re, codecs

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


# ur' ' won't work well, because each \u would have to be escaped
export_header = u'''
\\documentclass[10pt,a4paper,oneside,final]{article}

\\usepackage[margin=2cm]{geometry}

\\usepackage[T1]{fontenc}
\\usepackage[utf8]{inputenc}
\\usepackage[croatian]{babel}
\\usepackage[centertags,intlimits,namelimits,sumlimits]{amsmath}
\\usepackage{amsfonts}
\\usepackage{amssymb}
\\usepackage{enumitem}

\\usepackage[HTML]{xcolor}
\\definecolor{btn_primary}{HTML}{0055CC}
\\definecolor{css_gray}{HTML}{808080}

\\usepackage{fancyhdr}
\\fancypagestyle{empty}{
    \\fancyhf{}
    \\renewcommand{\\headrulewidth}{0pt}
    \\renewcommand{\\footrulewidth}{0pt}
}
\\fancypagestyle{plain}{
    \\fancyhf{}
    \\fancyfoot[R]{\\footnotesize\\bf\\thepage}
    \\renewcommand{\\headrulewidth}{0pt}
    \\renewcommand{\\footrulewidth}{0pt}
    \\renewcommand{\\footrule}{\\vskip-\\footrulewidth \\hrule width\\headwidth height\\footrulewidth}
}

\\usepackage{hyperref}
\\hypersetup{
    unicode=true,
    colorlinks=true,
    pdfborder={0 0 0},
    linkcolor=btn_primary,
    citecolor=btn_primary,
    filecolor=btn_primary,
    urlcolor=btn_primary,
    pdfstartpage={1},
    pdfstartview=FitH,
    pdfnewwindow=true
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
    \\subsection*{\\color{btn_primary}%(title)s}
    \\begin{flushright}\\url{http://skoljka.no-ip.org%(url)s}\\par\\footnotesize\\color{css_gray}\\textbf{Izvor:} IZVOR OVDJE\\end{flushright}
    %(content)s
'''

export_footer = u'''
\\end{document}
'''

tex_preamble = r'''
\documentclass{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[centertags,intlimits,namelimits,sumlimits]{amsmath}
\usepackage{amsthm}
\usepackage{amssymb}
\usepackage[active]{preview}
\pagestyle{empty}
\DeclareMathOperator{\tg}{tg}
\DeclareMathOperator{\ctg}{ctg}
\begin{document}
\begin{preview}
'''

# TODO: enable client-side caching
# TODO: join depth queries
def generate_png(eq, format):
    eq_hash = hashlib.md5((eq+format).encode('utf-8')).hexdigest()
    try:
        latex_element = LatexElement.objects.only("depth").get(hash=eq_hash)
        return eq_hash, latex_element.depth
    except:
        pass

    path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, 'm', eq_hash[0], eq_hash[1], eq_hash[2]))
    if not os.path.exists(path):
        os.makedirs(path)

    filename = os.path.normpath(os.path.join(path, eq_hash))

    
    f = codecs.open(filename + '.tex', 'w', encoding='utf-8')
    f.write(tex_preamble)
    f.write(unicode(format) % eq)
    f.write('\end{preview}\end{document}')
    f.close()
    
    # TODO: handle errors
    # TODO: disable logs
    cmd = '%s -output-directory=%s -interaction=batchmode %s.tex' % (latex_full_filename('latex'), os.path.dirname(filename), filename)
    error = run_command(cmd, timeout=5)
        
    if not error:
        # TODO: handle errors and test quality
        cmd = "%s -bg Transparent --gamma 1.5 -D 120 --depth* -T tight --strict -o %s.png %s" % (latex_full_filename('dvipng'), filename, filename)
        svgcmd = "%s -p 1 -n -o %s.svg %s" % (latex_full_filename('dvisvgm'), filename, filename)
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

    if not error and status == 0:
        os.remove(filename + '.tex')
        os.remove(filename + '.log')
        os.remove(filename + '.aux')
        os.remove(filename + '.dvi')

    latex_element = LatexElement(hash=eq_hash, text=eq, format=format, depth=depth)
    latex_element.save(force_insert=True)
    
    return eq_hash, depth


tex_preamble_svg = r'''
\documentclass[12pt]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[centertags,intlimits,namelimits,sumlimits]{amsmath}
\usepackage{amsthm}
\usepackage{amssymb}
\usepackage[active]{preview}
\pagestyle{empty}
\DeclareMathOperator{\tg}{tg}
\DeclareMathOperator{\ctg}{ctg}
\begin{document}
'''

depth_out_1 = r'''
\newwrite\outputstream
\immediate\openout\outputstream='''
depth_out_2 = r'''
\immediate\write\outputstream{box_height=\the\ht0,box_depth=\the\dp0,box_width=\the\wd0}
\immediate\closeout\outputstream
'''

# TODO: enable client-side caching
# TODO: join depth queries
def generate_svg(eq, format, inline):
    eq_hash = hashlib.md5((eq+format).encode('utf-8')).hexdigest()
    # try:
        # latex_element = LatexElement.objects.only("depth").get(hash=eq_hash)
        # return eq_hash, latex_element.depth
    # except:
        # pass

    path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, 'm', eq_hash[0], eq_hash[1], eq_hash[2]))
    if not os.path.exists(path):
        os.makedirs(path)

    filename = os.path.normpath(os.path.join(path, eq_hash))


    f = codecs.open(filename + '.tex', 'w', encoding='utf-8')
    f.write(tex_preamble_svg)
    f.write(r'''\newcommand{\MYFORMULA}{''' + (unicode(format) % eq) + '}')
    if inline:
        f.write('\setbox0\hbox{\MYFORMULA}')
    f.write(r'''\begin{preview}\MYFORMULA\end{preview}''')
    if inline:
        f.write(depth_out_1 + unicode(eq_hash + '.dat') + depth_out_2)
    f.write('\end{document}')
    f.close()

    # TODO: handle errors
    # TODO: disable logs
    cmd = '%s -output-directory=%s -interaction=batchmode %s.tex' % (latex_full_filename('latex'), os.path.dirname(filename), filename)
    error = run_command(cmd, timeout=5)

    if not error:
        cmd = "%s -p 1 -n -o %s.svg %s.dvi" % (latex_full_filename('dvisvgm'), filename, filename)
        status, stdout = getstatusoutput(cmd) # there is a bug in the latest dvisvgm version - there are TeX pt's in SVG file instead of CSS pt's
        print stdout

    if not error and status == 0 and not inline:
        depth = 0
    elif not error and status == 0 and inline:
        page_size_re = re.compile('\s*page size: (\d+\.\d+)pt x (\d+\.\d+)pt \((\d+\.\d+)mm x (\d+\.\d+)mm\)')
        for line in stdout.splitlines():
            print line
            m = page_size_re.match(line)
            if m:
                height = float(m.group(2)) # these are TeX pt's (1in = 72.27pt)
                height = height * 72 / 72.27 # these are CSS pt's (1in = 72pt)
                break

        # open .dat file, parse and set depth with following formula
        f = open(filename + '.dat', 'r')
        line = f.readline()
        f.close()

        dat_file_re = re.compile('box_height=(\d+\.\d+)pt,box_depth=(\d+\.\d+)pt,box_width=(\d+\.\d+)pt')
        m = dat_file_re.match(line)
        if m:
            box_height = float(m.group(1))
            box_depth = float(m.group(2))
            box_width = float(m.group(3))
            depth = height * box_depth / (box_depth + box_height)
            print depth
        else:
            depth = ERROR_DEPTH_VALUE
    else: # error
        depth = ERROR_DEPTH_VALUE

    # if not error and status == 0:
        # os.remove(filename + '.tex')
        # os.remove(filename + '.log')
        # os.remove(filename + '.aux')
        # os.remove(filename + '.dvi')
        # os.remove(filename + '.dat')

    latex_element = LatexElement(hash=eq_hash, text=eq, format=format, depth=depth)
    # latex_element.save(force_insert=True)

    return eq_hash, depth
