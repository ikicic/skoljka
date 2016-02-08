from django.conf import settings
from django.db import models
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string

from skoljka.libs.decorators import autoconnect
from skoljka.libs.generators import LowerNumKeyGen
from skoljka.libs.string_operations import media_path_to_url

import os

# TODO: napraviti MathContentField koji ce se sam spremiti
# pri spremanju forme, ako je to uopce moguce

ERROR_DEPTH_VALUE = -1000
MAX_LENGTH = 100000
IMG_URL_PATH = '/media/m/'
TYPE_HTML = 0
TYPE_LATEX = 1


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
    text = models.TextField(blank=True, max_length=MAX_LENGTH,
        verbose_name='Tekst')
    html = models.TextField(blank=True, null=True)
    # version = models.IntegerField(default=0)

    def __unicode__(self):
        return self.short()

    def short(self, length=50):
        return self.text[:length] + "..." if len(self.text) > length else self.text

    def is_empty(self):
        return not self.text or self.text.isspace()

    def pre_save(self):
        if not hasattr(self, '_no_html_reset'):
            self.html = None

    def render(self, quote=False):
        if self.html is None:
            from mathcontent.utils import convert_to_html
            print 'CONVERTING %d...' % self.id
            self.html = convert_to_html(self.text, content=self)
            self._no_html_reset = True
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


def attachment_upload_to(instance, filename):
    return os.path.join(
        settings.MEDIA_ROOT,
        'attachment',
        str(instance.id // 100),
        '%05d_%s' % (instance.id, LowerNumKeyGen.generate(length=20)),
        filename
    )

class Attachment(models.Model):
    file = models.FileField(max_length=500, upload_to=attachment_upload_to,
            blank=True)
    content = models.ForeignKey(MathContent, related_name='attachments')
    date_created = models.DateTimeField(auto_now_add=True)

    cache_file_size = models.IntegerField(default=0)

    def __unicode__(self):
        if self.cache_file_size >= 0:
            return 'Attachment #{}'.format(self.id)
        else:
            return 'Attachment #{} <MISSING>'.format(self.id)

    def get_url(self):
        return media_path_to_url(self.file.name)

    def get_filename(self):
        return os.path.basename(self.file.name)

    def get_full_path_and_filename(self):
        return self.file.name
