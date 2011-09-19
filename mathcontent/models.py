from django.db import models
from django.template.loader import render_to_string
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

imgpath = 'media/image/math/'
lformat = "$%s$ \n \\newpage \n"
cformat = "\\[\n%s \n\\] \n \\newpage \n"
# KOKAN

# KOKAN
def generatepng(eq, format):
    eqHash = hashlib.md5(eq).hexdigest()
    
    # TODO: if image already exists, don't render again, just return hash
    # TODO: what if two eqs have equal hashes? very small probability, but...
    
    cwd = os.getcwd()
    os.chdir(os.path.abspath(imgpath))
    f = open(eqHash + '.tex', 'w')
    f.write(tex_preamble)
    f.write(format % eq)
    f.write('\end{document}')
    f.close()
    
    # TODO: handle errors
    os.system('latex %s' % eqHash)
    # TODO: handle errors and test quality
    cmd = "dvipng -T tight -x 1200 -z 9 -bg transparent -o %s.png %s" % (eqHash, eqHash)
    os.system(cmd)
    
    # os.remove(eqHash + '.tex')
    # os.remove(eqHash + '.log')
    # os.remove(eqHash + '.aux')
    # os.remove(eqHash + '.dvi')
    
    os.chdir(cwd)
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
            html = html.replace(("[lmath]%s[/lmath]" % eq), "<span class=\"eq\"><img src=\"{{ MEDIA_URL }}%s%s.png\" alt=\"%s\"/></span>" % (imgpath, eqHash, eqHash))
        
        for eq in cmaths:
            eqHash = generatepng(eq, cformat)
            html = html.replace(("[cmath]%s[/cmath]" % eq), "<div class=\"eq\"><img src=\"{{ MEDIA_URL }}%s%s.png\" alt=\"%s\"/></div>" % (imgpath, eqHash, eqHash))
        
        return html
        # return render_to_string('mathcontenttext.html', {'text': html})
    # KOKAN
