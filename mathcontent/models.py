from django.db import models
from django.utils.safestring import mark_safe

import re
import utils.xss

inline_format = "$%s$ \n \\newpage \n"
block_format = "\\[\n%s \n\\] \n \\newpage \n"

img_path = 'mathcontent/static/math/'
img_url_path = 'static/math/'

# TODO: napraviti MathContentField koji ce se sam spremiti
# pri spremanju forme, ako je to uopce moguce




class LatexElement(models.Model):
    hash = models.CharField(max_length=32, primary_key=True)
    text = models.TextField()
    format = models.CharField(max_length=64)
    depth = models.IntegerField()


class MathContent(models.Model):
    text = models.TextField();
    
    class Admin:
        pass
    
    def __unicode__(self):
        return self.text
        
    def short(self, length=50):
        return self.text[:length] + "..." if len(self.text) > length else self.text
    
    # TODO: podrska za $, tj. \$ u tekstu zadatka
    # TODO: optimizirati queryje za depth
    # latex se treba renderirati samo kod uploadata / edita
    # (ili npr. da postoji neki flag je je latex vec generiran, to se moze povezati s depth cache-om)
    def render(self): # XSS danger!!! Be careful
        from mathcontent.latex import generate_png
        html = utils.xss.escape(self.text)

        blk_re = re.compile(r'\$\$(.*?)\$\$', re.DOTALL)
        blk_maths = blk_re.findall(html)

        for eq in blk_maths:
            eq_hash, depth = generate_png(utils.xss.unescape(eq), block_format)
            new = '<img src="/%s%s.png" alt="%s" class="latex_center">' % (img_url_path, eq_hash, eq)
            html = html.replace("$$%s$$" % eq, new)

        inl_re = re.compile('\$(.*?)\$', re.DOTALL)
        inl_maths = inl_re.findall(html)

        for eq in inl_maths:
            eq_hash, depth = generate_png(utils.xss.unescape(eq), inline_format)
            new = '<img src="/%s%s.png" alt="%s" class="latex" style="vertical-align:%dpx">' % (img_url_path, eq_hash, eq, -depth)
            html = html.replace("$%s$" % eq, new)

        # Html files don't support newlines in the standard way.
        # This is for added user ability to format text
        return mark_safe(html.replace("\r\n", "<br>"))

    # TODO: performace test
    def convert_to_latex(self):
        # replaces # % ^ & _ { } ~ \
        # with \# \% \textasciicircum{} \& \_ \{ \} \~{} \textbackslash{}
        # keeps \$ as \$, because $ is a special char anyway

        esc = {'#': '\\#'
            , '%': '\\%'
            , '^': '\\textasciicircum{}'
            , '&': '\\&'
            , '_': '\\_'
            , '{': '\\{'
            , '}': '\\}'
            , '~': '\\~{}'
            , '\\': '\\textbackslash{}'}
        out = []
        
        s = self.text
        n = len(s)
        i = 0
        while i < n:
            if s[i] == '\\':
                if i + 1 < n:
                    out.append(s[i:i+2])
                # else: report error
                i += 2
            elif s[i] == '$':
                # copy string between $ $ or $$ $$
                while i < n and s[i] == '$':
                    out.append('$')
                    i += 1
                while i < n:
                    if s[i] == '\\':
                        if i + 1 < n:
                            out.append(s[i:i+2])
                        # else: report error
                        i += 2;
                    elif s[i] == '$':
                        break;
                    else:
                        out.append(s[i])
                        i += 1
                while i < n and s[i] == '$':
                    out.append('$')
                    i += 1                        
            else:
                out.append(esc.get(s[i],s[i]))
                i += 1

        return u''.join(out)
