from django.db import models

import re
import utils.xss
from mathcontent.latex import generate_png

inline_format = "$%s$ \n \\newpage \n"
block_format = "\\[\n%s \n\\] \n \\newpage \n"
# TODO(gzuzic): is this used at all?
img_path = 'mathcontent/static/math/'
img_url_path = 'static/math/'


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

        # TODO(gzuzic): 114 character line?! C'mon :) We should shrink that to ~80
        for eq in blk_maths:
            eq_hash = generate_png(utils.xss.unescape(eq), block_format)
            new = "<div class=\"latex\"><img src=\"/%s%s.png\" alt=\"%s\"/></div>" % (img_url_path, eq_hash, eq)
            html = html.replace("$$%s$$" % eq, new)

        inl_re = re.compile('\$(.*?)\$', re.DOTALL)
        inl_maths = inl_re.findall(html)

        for eq in inl_maths:
            eq_hash = generate_png(utils.xss.unescape(eq), inline_format)
            new = "<span class=\"latex\"><img src=\"/%s%s.png\" alt=\"%s\"/></span>" % (img_url_path, eq_hash, eq)
            html = html.replace("$%s$" % eq, new)

        # Html files don't support newlines in the standard way.
        # This is for added user ability to format text
        return html.replace("\r\n", "<br>")
