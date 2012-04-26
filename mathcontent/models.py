from django.conf import settings
from django.db import models
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string

from skoljka.utils.decorators import autoconnect
from skoljka.utils.generators import LowerNumKeyGen

import os
import re

# TODO: napraviti MathContentField koji ce se sam spremiti
# pri spremanju forme, ako je to uopce moguce


MAX_LENGTH = 100000

class LatexElement(models.Model):
    hash = models.CharField(max_length=32, primary_key=True)
    text = models.TextField()
    format = models.CharField(max_length=64)
    depth = models.IntegerField()
    date_created = models.DateTimeField(auto_now=True, help_text=('If something goes wrong, you would like to have this information.'))
    # Mjera sigurnosti, dogodilo se da se latex zblokira.
    # Ne znam razlog, ovime se nadam da ce se olaksati debugiranje.


@autoconnect
class MathContent(models.Model):
    text = models.TextField(max_length=MAX_LENGTH, verbose_name='Tekst')
    html = models.TextField(blank=True, null=True)
    
    def __unicode__(self):
        return self.short()
        
    def short(self, length=50):
        return self.text[:length] + "..." if len(self.text) > length else self.text
    
    def pre_save(self):
        if not hasattr(self, 'no_html_reset'):
            self.html = None
    
    def render(self, quote=False):
        if self.html is None:
            from mathcontent.utils import convert_to_html
            print 'CONVERTING %d...' % self.id
            self.html = convert_to_html(self.text, self)
            self.no_html_reset = True
            self.save()
            print 'DONE!'
        
        return render_to_string('inc_mathcontent_render.html', {
            'content': self,
            # TODO: make a template tag
            # 'view_source': request.user.is_authenticated(),
            'view_source': True,
            'quote': quote,
        })
        
    # TODO: template tag!
    def render_quote(self):
        return self.render(quote=True)

    def convert_to_latex(self):
        from mathcontent.utils import convert_to_latex as _convert_to_latex
        return _convert_to_latex(self.text, self)


def attachment_upload_to(instance, filename):
    return os.path.join(
        settings.MEDIA_ROOT,
        'attachment',
        str(instance.id // 100),
        '%05d_%s' % (instance.id, LowerNumKeyGen.generate(length=20)),
        filename
    )

class Attachment(models.Model):
    file = models.FileField(upload_to=attachment_upload_to, blank=True)
    content = models.ForeignKey(MathContent, related_name='attachments')
    date_created = models.DateTimeField(auto_now_add=True)

    def get_url(self):
        # FIXME: this is risky...
        # file.name includes path
        return settings.MEDIA_URL + self.file.name[len(settings.MEDIA_ROOT)+1:]

    def get_filename(self):
        return os.path.basename(self.file.name)
        
    def get_full_path_and_filename(self):
        return self.file.name
