from collections import defaultdict
import codecs
import hashlib
import os
import re
import sys

from django.conf import settings
from django.template.loader import render_to_string

from skoljka.utils.timeout import run_command

from skoljka.mathcontent.models import ERROR_DEPTH_VALUE, LatexElement

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

def latex_escape(val):
    return u"".join(latex_escape_table.get(x, x) for x in val)


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
