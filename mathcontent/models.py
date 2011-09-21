from django.db import models

# This one requires django-model-utils to be installed (pip can help)
from model_utils.managers import InheritanceManager

# TODO(gzuzic): measure the number of SQL queries made and whether
#               can it be improved
class MathContent(models.Model):
    objects = InheritanceManager();
    
    def __unicode__(self):
        """Polymorphically call a deriving class member __unicode__()"""
        return MathContent.objects.select_subclasses().get(id=self.id).__unicode__()
    
    def render(self):
        """Polymorphically call a deriving class member render()"""
        return MathContent.objects.select_subclasses().get(id=self.id).render()

import re
import utils.xss
from mathcontent.latex import generate_png

lformat = "$%s$ \n \\newpage \n"
cformat = "\\[\n%s \n\\] \n \\newpage \n"
imgpath = 'mathcontent/static/math/'
imgurlpath = 'static/math/'

class MathContentText(MathContent):
    text = models.TextField();
    
    def __unicode__(self):
        return self.text
    
    def render(self): # XSS danger!!! Be careful

        # TODO(gzuzic): This should probably get optimised for speed?
        lRe = re.compile('\[lmath\](.*?)\[/lmath\]', re.DOTALL)
        cRe = re.compile('\[cmath\](.*?)\[/cmath\]', re.DOTALL)
        html = utils.xss.escape(self.text)
        lmaths = lRe.findall(html)
        cmaths = cRe.findall(html)

        for eq in lmaths:
            eqHash = generate_png(utils.xss.unescape(eq), lformat)
            # TODO: espace chars for eq
            html = html.replace(("[lmath]%s[/lmath]" % eq), "<span class=\"eq\"><img src=\"/%s%s.png\" alt=\"%s\"/></span>" % (imgurlpath, eqHash, eq))
        
        for eq in cmaths:
            eqHash = generate_png(utils.xss.unescape(eq), cformat)
            # TODO: espace chars for eq
            html = html.replace(("[cmath]%s[/cmath]" % eq), "<div class=\"eq\"><img src=\"/%s%s.png\" alt=\"%s\"/></div>" % (imgurlpath, eqHash, eq))        

        return html
