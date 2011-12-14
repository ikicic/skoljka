from django.db import models
from django.utils.safestring import mark_safe

import re
import utils.xss
from mathcontent.latex import generate_png

inline_format = "$%s$ \n \\newpage \n"
block_format = "\\[\n%s \n\\] \n \\newpage \n"
# TODO(gzuzic): is this used at all?
img_path = 'mathcontent/static/math/'
img_url_path = 'static/math/'

# TODO: napraviti MathContentField koji ce se sam spremiti
# pri spremanju forme, ako je to uopce moguce

class MathContent(models.Model):
    text = models.TextField();
    
    class Admin:
        pass
    
    def __unicode__(self):
        return self.text
        
        
    def short(self, length=50):
        return self.text[:length] + "..." if len(self.text) > length else self.text
    
    def render(self): # XSS danger!!! Be careful
        html = utils.xss.escape(self.text)

        blk_re = re.compile(r'\$\$(.*?)\$\$', re.DOTALL)
        blk_maths = blk_re.findall(html)

        for eq in blk_maths:
            eq_hash = generate_png(utils.xss.unescape(eq), block_format)
            new = '<img src="/%s%s.png" alt="%s" class="latex_center">' % (img_url_path, eq_hash, eq)
            html = html.replace("$$%s$$" % eq, new)

        inl_re = re.compile('\$(.*?)\$', re.DOTALL)
        inl_maths = inl_re.findall(html)

        for eq in inl_maths:
            eq_hash = generate_png(utils.xss.unescape(eq), inline_format)
            new = '<img src="/%s%s.png" alt="%s" class="latex">' % (img_url_path, eq_hash, eq)
            html = html.replace("$%s$" % eq, new)

        # Html files don't support newlines in the standard way.
        # This is for added user ability to format text
        return mark_safe(html.replace("\r\n", "<br>"))
