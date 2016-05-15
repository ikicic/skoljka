from django.conf import settings
from django.utils.translation import ugettext as _

from skoljka.libs import xss
from skoljka.libs.timeout import run_command

from mathcontent.forms import AttachmentForm
from mathcontent.models import Attachment, TYPE_HTML, TYPE_LATEX
from mathcontent import converter_v0
from mathcontent import converter_v1

import os

def convert(type, text, content=None, attachments_path=None):
    """Call the right converter to convert given text to HTML or LaTeX."""
    if text.startswith(converter_v0.VERSION_MARKER):
        text = text[len(converter_v0.VERSION_MARKER):]
        converter = converter_v0
    else:
        converter = converter_v1

    attachments = content and list(Attachment.objects.filter(content=content))
    try:
        return converter.convert(type, text, attachments=attachments,
                attachments_path=attachments_path)
    except:
        if settings.DEBUG:
            raise
        msg = _("Internal parser error. Please contact administrators.")
        if type == TYPE_HTML:
            return "<span style=\"color:red;\">{}</span>".format(msg)
        return msg


def convert_to_html(*args, **kwargs):
    """Shortcut function for `convert`."""
    return convert(TYPE_HTML, *args, **kwargs)

def convert_to_latex(*args, **kwargs):
    """Shortcut function for `convert`."""
    return convert(TYPE_LATEX, *args, **kwargs)


def check_and_save_attachment(request, content):
    """
        Check if AttachmentForm is valid and, if it is, automatically save
        Attachment model. Moved to a separate util method, because it is quite
        complex to repeat

        Returns pair (attachment, form).
    """

    form = AttachmentForm(request.POST, request.FILES)

    if form.is_valid():
        # First generate attachment instance, so that file name generation works.
        attachment = Attachment(content=content)
        attachment.save()

        # Generate path and file name etc.
        form = AttachmentForm(request.POST, request.FILES, instance=attachment)
        attachment = form.save(commit=False)

        # Make file name compatible with LaTeX.
        name = attachment.file.name.replace(' ', '')
        if '.' in name:
            name, ext = name.rsplit('.', 1)
            name = name.replace('.', '') + '.' + ext
        attachment.file.name = name
        attachment.cache_file_size = attachment.file.size
        attachment.save()

        # Refresh HTML
        # TODO: use signals!
        content.html = None
        content.save()
    else:
        attachment = None

    return attachment, form


class ThumbnailRenderingException(Exception):
    pass

def create_file_thumbnail(filename):
    filename_no_ext, ext = os.path.splitext(filename)
    if not ext or ext[0] != '.':
        return
    ext = ext[1:]
    if ext not in ['pdf', 'ps', 'jpg', 'jpeg', 'bmp', 'png', 'svg']:
        return
    thumbnail_name = filename_no_ext + '-thumb200x150.png'
    cmd = "convert -thumbnail '200x150^' -crop 200x150+0+0 +repage {}[0] {}"
    cmd = cmd.format(filename, thumbnail_name)

    error = run_command(cmd, timeout=5)
    if error:
        raise ThumbnailRenderingException(error)

    return thumbnail_name
