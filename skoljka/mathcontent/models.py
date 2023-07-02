import os

from django.conf import settings
from django.db import models

from skoljka.utils.decorators import autoconnect
from skoljka.utils.generators import LowerNumKeyGen
from skoljka.utils.string_operations import media_path_to_url

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
    date_created = models.DateTimeField(
        auto_now=True, help_text="If something goes wrong, date might be useful."
    )


@autoconnect
class MathContent(models.Model):
    text = models.TextField(blank=True, max_length=MAX_LENGTH, verbose_name='Tekst')
    html = models.TextField(blank=True, null=True)
    # version = models.IntegerField(default=0)

    def __unicode__(self):
        return self.short()

    def short(self, length=30):
        return self.text[:length] + "..." if len(self.text) > length else self.text

    def is_empty(self):
        return not self.text or self.text.isspace()

    def pre_save(self):
        if not hasattr(self, '_no_html_reset'):
            self.html = None

    def get_edit_attachments_url(self):
        return '/mathcontent/{}/attachments/'.format(self.id)


def attachment_upload_to(instance, filename):
    return os.path.join(
        settings.MEDIA_ROOT,
        'attachment',
        str(instance.id // 100),
        '%05d_%s' % (instance.id, LowerNumKeyGen.generate(length=20)),
        filename,
    )


class Attachment(models.Model):
    file = models.FileField(max_length=500, upload_to=attachment_upload_to)
    content = models.ForeignKey(MathContent, related_name='attachments')
    date_created = models.DateTimeField(auto_now_add=True)

    cache_file_size = models.IntegerField(default=0)

    def __unicode__(self):
        if self.cache_file_size >= 0:
            return "Attachment #{}".format(self.id)
        else:
            return "Attachment #{} <MISSING>".format(self.id)

    def get_url(self):
        return media_path_to_url(self.file.name)

    def get_filename(self):
        return os.path.basename(self.file.name)

    def get_full_path_and_filename(self):
        return self.file.name

    def delete_file(self):
        """Delete the file and its parent folder."""
        path = self.file.name
        if path:
            # Empty path can happen when the state is corrupt.
            # TODO: Error log?
            self.file.delete()
            os.rmdir(os.path.dirname(path))
