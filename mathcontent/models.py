from django.db import models
from django.template.loader import render_to_string
from django.conf import settings
from model_utils.managers import InheritanceManager

# KOKAN
import re, os, sys, hashlib

tex_preamble = r'''
\documentclass{article}
\usepackage{amsmath}
\usepackage{amsthm}
\usepackage{amssymb}
\pagestyle{empty}
\begin{document}
'''

imgpath = 'mathcontent/static/math/'
imgurlpath = 'static/math/'
lformat = "$%s$ \n \\newpage \n"
cformat = "\\[\n%s \n\\] \n \\newpage \n"
# KOKAN

# KOKAN
# TODO: enable client-side caching
def generatepng(eq, format):
    eqHash = hashlib.md5(eq+format).hexdigest()
    
    # TODO: what if two eqs have equal hashes? very small probability, but...
    
    filename = os.path.normpath(os.path.join(settings.PROJECT_ROOT, 'mathcontent/static/math/' + eqHash))

    if os.path.exists( filename + '.png' ):
        return eqHash
    

    f = open( filename + '.tex', 'w')
    f.write(tex_preamble)
    f.write(format % eq)
    f.write('\end{document}')
    f.close()
    
    # TODO: handle errors
    # TODO: disable logs
    os.system('latex -output-directory=%s %s.tex' % (os.path.dirname(filename), filename) )
    # TODO: handle errors and test quality
    cmd = "dvipng -bg Transparent --gamma 1.5 -D 120 -T tight --strict -o %s.png %s" % (filename, filename)
    os.system(cmd)
    
    # os.remove(eqHash + '.tex')
    # os.remove(eqHash + '.log')
    # os.remove(eqHash + '.aux')
    # os.remove(eqHash + '.dvi')
    
    return eqHash
# KOKAN


# TODO(gzuzic): measure the number of SQL queries made and whether can it be improved

class MathContent(models.Model):
    objects = InheritanceManager();
    
    def __unicode__(self):
        """Polymorphically call a deriving class member __unicode__()"""
        return MathContent.objects.select_subclasses().get(id=self.id).__unicode__()
    
    def render(self):
        """Polymorphically call a deriving class member render()"""
        return MathContent.objects.select_subclasses().get(id=self.id).render()


class MathContentText(MathContent):
    text = models.TextField();
    
    def __unicode__(self):
        return self.text
    
    # KOKAN
    def render(self):
        lRe = re.compile('\[lmath\](.*?)\[/lmath\]')
        cRe = re.compile('\[cmath\](.*?)\[/cmath\]')
        
        html = self.text
        
        lmaths = lRe.findall(self.text)
        cmaths = cRe.findall(self.text)
        
        for eq in lmaths:
            eqHash = generatepng(eq, lformat)
            # TODO: espace chars for eq
            html = html.replace(("[lmath]%s[/lmath]" % eq), "<span class=\"eq\"><img src=\"/%s%s.png\" alt=\"%s\"/></span>" % (imgurlpath, eqHash, eq))
        
        for eq in cmaths:
            eqHash = generatepng('\displaystyle' + eq, cformat)
            # TODO: espace chars for eq
            html = html.replace(("[cmath]%s[/cmath]" % eq), "<div class=\"eq\"><img src=\"/%s%s.png\" alt=\"%s\"/></div>" % (imgurlpath, eqHash, eq))
        
        return html
        # return render_to_string('mathcontenttext.html', {'text': html})
    # KOKAN
