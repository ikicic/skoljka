from django.conf import settings
from django.db import models
from django.utils.safestring import mark_safe

from skoljka.utils.decorators import autoconnect
from skoljka.utils.generators import LowerNumKeyGen

import os
import re

# TODO: napraviti MathContentField koji ce se sam spremiti
# pri spremanju forme, ako je to uopce moguce




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
    text = models.TextField()
    html = models.TextField()
    
    class Admin:
        pass
    
    def __unicode__(self):
        return self.text
        
    def short(self, length=50):
        return self.text[:length] + "..." if len(self.text) > length else self.text
    
    def pre_save(self):
        if not hasattr(self, 'no_html_reset'):
            self.html = None
    
    def render(self):
        if self.html is not None:
            return mark_safe(self.html)
            
        from mathcontent.utils import convert_to_html
        print 'CONVERTING %d...' % self.id
        self.html = convert_to_html(self.text)
        self.no_html_reset = True
        self.save()
        print 'DONE!'
        
        return mark_safe(self.html)

    def convert_to_latex(self):
        from mathcontent.utils import convert_to_latex as _convert_to_latex
        return _convert_to_latex(self.text)


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
        
