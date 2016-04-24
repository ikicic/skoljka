from django.conf import settings
from django.template.loader import render_to_string

from mathcontent.models import ERROR_DEPTH_VALUE, LatexElement

from skoljka.libs.timeout import run_command

from collections import defaultdict
import codecs
import hashlib
import os
import re
import sys

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
    path = os.path.join(getattr(settings, 'LATEX_BIN_DIR', ''), filename)
    return ('"%s"' if mswindows else '%s') % path


def get_available_latex_elements(formulas):
    """`formulas` is a list of (hash, format, content)."""
    # MySQL doesn't optimize IN when used with pairs, so we do one query per
    # format.
    groups = defaultdict(list)
    for hash, format, content in formulas:
        groups[format].append(hash)
    result = []
    for format, hashes in groups.iteritems():
        result.extend(LatexElement.objects.filter(
            format=format, hash__in=hashes))
    return result


def generate_latex_hash(format, content):
    return hashlib.md5((content.strip() + format).encode('utf-8')).hexdigest()


def get_or_generate_png(format, content):
    """Get LatexElement for the given (format, content) pair or generate if it
    doesn't exist yet."""
    hash = generate_latex_hash(format, content)
    try:
        return LatexElement.objects.only('depth').get(hash=hash)
    except LatexElement.DoesNotExist:
        pass
    return generate_png(hash, format, content)


# TODO: enable client-side caching
# TODO: join depth queries
def generate_png(hash, format, latex):
    latex = latex.strip()
    path = os.path.normpath(os.path.join(
        settings.MEDIA_ROOT, 'm', hash[0], hash[1], hash[2]))
    if not os.path.exists(path):
        os.makedirs(path)
    filename = os.path.normpath(os.path.join(path, hash))

    f = codecs.open(filename + '.tex', 'w', encoding='utf-8')
    data = {'equation': unicode(format) % latex}
    f.write(render_to_string('latex_inline.tex', data))
    f.close()

    # TODO: handle errors
    # TODO: disable logs
    cmd = '%s -output-directory=%s -interaction=batchmode %s.tex' % \
            (latex_full_filename('latex'), os.path.dirname(filename), filename)
    error = run_command(cmd, timeout=5)

    if not error:
        # TODO: handle errors and test quality
        cmd = "%s -bg Transparent --gamma 1.5 -D 120 --depth* -T tight --strict -o %s.png %s" % (latex_full_filename('dvipng'), filename, filename)
        status, stdout = getstatusoutput(cmd)

    # Fixing $\newline$ bug. dvipng would return depth=2^31-1.
    # In case we get something like this, do not output weird html, rather mark
    # the latex as invalid.
    MAX_DEPTH = 10000

    depth = ERROR_DEPTH_VALUE
    if not error and status == 0:
        depth_re = re.compile(r'.*\[\d+ depth=(-?\d+)\]')
        for line in stdout.splitlines():
            m = depth_re.match(line.strip())
            if m:
                depth = int(m.group(1))
                break
        if depth > MAX_DEPTH:
            depth = ERROR_DEPTH_VALUE
        if depth == ERROR_DEPTH_VALUE:
            print 'ERROR stdout:', stdout

    if not error and status == 0:
        os.remove(filename + '.tex')
        os.remove(filename + '.log')
        os.remove(filename + '.aux')
        os.remove(filename + '.dvi')

    latex_element = LatexElement(
            hash=hash, text=latex, format=format, depth=depth)
    latex_element.save(force_insert=True)
    return latex_element


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

# # TODO: enable client-side caching
# # TODO: join depth queries
# def generate_svg(eq, format, inline):
#     eq_hash = hashlib.md5((eq+format).encode('utf-8')).hexdigest()
#     # try:
#         # latex_element = LatexElement.objects.only("depth").get(hash=eq_hash)
#         # return eq_hash, latex_element.depth
#     # except:
#         # pass
#
#     path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, 'm', eq_hash[0], eq_hash[1], eq_hash[2]))
#     if not os.path.exists(path):
#         os.makedirs(path)
#
#     filename = os.path.normpath(os.path.join(path, eq_hash))
#
#
#     f = codecs.open(filename + '.tex', 'w', encoding='utf-8')
#     f.write(tex_preamble_svg)
#     f.write(r'''\newcommand{\MYFORMULA}{''' + (unicode(format) % eq) + '}')
#     if inline:
#         f.write('\setbox0\hbox{\MYFORMULA}')
#     f.write(r'''\begin{preview}\MYFORMULA\end{preview}''')
#     if inline:
#         f.write(depth_out_1 + unicode(eq_hash + '.dat') + depth_out_2)
#     f.write('\end{document}')
#     f.close()
#
#     # TODO: handle errors
#     # TODO: disable logs
#     cmd = '%s -output-directory=%s -interaction=batchmode %s.tex' % (latex_full_filename('latex'), os.path.dirname(filename), filename)
#     error = run_command(cmd, timeout=5)
#
#     if not error:
#         cmd = "%s -p 1 -n -o %s.svg %s.dvi" % (latex_full_filename('dvisvgm'), filename, filename)
#         status, stdout = getstatusoutput(cmd) # there is a bug in the latest dvisvgm version - there are TeX pt's in SVG file instead of CSS pt's
#         print stdout
#
#     if not error and status == 0 and not inline:
#         depth = 0
#     elif not error and status == 0 and inline:
#         page_size_re = re.compile('\s*page size: (\d+\.\d+)pt x (\d+\.\d+)pt \((\d+\.\d+)mm x (\d+\.\d+)mm\)')
#         for line in stdout.splitlines():
#             print line
#             m = page_size_re.match(line)
#             if m:
#                 height = float(m.group(2)) # these are TeX pt's (1in = 72.27pt)
#                 height = height * 72 / 72.27 # these are CSS pt's (1in = 72pt)
#                 break
#
#         # open .dat file, parse and set depth with following formula
#         f = open(filename + '.dat', 'r')
#         line = f.readline()
#         f.close()
#
#         dat_file_re = re.compile('box_height=(\d+\.\d+)pt,box_depth=(\d+\.\d+)pt,box_width=(\d+\.\d+)pt')
#         m = dat_file_re.match(line)
#         if m:
#             box_height = float(m.group(1))
#             box_depth = float(m.group(2))
#             box_width = float(m.group(3))
#             depth = height * box_depth / (box_depth + box_height)
#             print depth
#         else:
#             depth = ERROR_DEPTH_VALUE
#     else: # error
#         depth = ERROR_DEPTH_VALUE
#
#     # if not error and status == 0:
#         # os.remove(filename + '.tex')
#         # os.remove(filename + '.log')
#         # os.remove(filename + '.aux')
#         # os.remove(filename + '.dvi')
#         # os.remove(filename + '.dat')
#
#     latex_element = LatexElement(hash=eq_hash, text=eq, format=format, depth=depth)
#     # latex_element.save(force_insert=True)
#
#     return eq_hash, depth
