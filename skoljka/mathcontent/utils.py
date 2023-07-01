import os

from django.conf import settings
from django.utils.translation import ugettext as _

from skoljka.mathcontent import converter_v0, converter_v1
from skoljka.mathcontent.forms import AttachmentForm
from skoljka.mathcontent.models import TYPE_HTML, TYPE_LATEX, Attachment
from skoljka.utils import xss
from skoljka.utils.timeout import run_command


def convert(type, text, content=None, attachments_path=None):
    """Call the right converter to convert given text to HTML or LaTeX."""
    if text.startswith(converter_v0.VERSION_MARKER):
        text = text[len(converter_v0.VERSION_MARKER) :]
        converter = converter_v0
    else:
        converter = converter_v1

    attachments = content and list(
        Attachment.objects.filter(content=content).order_by('id')
    )
    return converter.convert(
        type, text, attachments=attachments, attachments_path=attachments_path
    )


def convert_safe(type, *args, **kwargs):
    try:
        return convert(type, *args, **kwargs)
    except:
        if getattr(settings, 'MATHCONTENT_DEBUG', False):
            raise
        msg = _("Internal parser error. Please contact administrators.")
        if type == TYPE_HTML:
            return u"<span style=\"color:red;\">{}</span>".format(msg)
        return msg


def convert_to_html(*args, **kwargs):
    """Shortcut function for `convert`."""
    return convert(TYPE_HTML, *args, **kwargs)


def convert_to_html_safe(*args, **kwargs):
    return convert_safe(TYPE_HTML, *args, **kwargs)


def convert_to_latex(*args, **kwargs):
    """Shortcut function for `convert`."""
    return convert(TYPE_LATEX, *args, **kwargs)


class _CheckEditAttachmentsPermissionsResult:
    """Placeholder for potentially more complicated attachment logic, in case
    we want to allow not only tasks but other models as well."""

    def __init__(self, allowed, task):
        self.allowed = allowed
        self.task = task


def check_edit_attachments_permissions(user, content):
    """Check whether the user is allowed to add and delete attachments.

    Currently, only Task MathContents are allowed to have attachments.
    Only users with Task EDIT permission can upload or delete them.
    """
    # If updating this, update edit_attachments as well.

    # Type-specific customization.
    from skoljka.task.models import Task

    try:
        task = Task.objects.get(content_id=content.id)
    except Task.DoesNotExist:
        return _CheckEditAttachmentsPermissionsResult(False, None)

    allowed = task.is_allowed_to_edit(user)
    return _CheckEditAttachmentsPermissionsResult(allowed, task)


def check_and_save_attachment(request, content):
    """
    Check if AttachmentForm is valid and, if it is, automatically save
    Attachment model. Moved to a separate util method, because it is quite
    complex to repeat

    Returns pair (attachment, form).
    """

    form = AttachmentForm(request.POST, request.FILES)
    if form.is_valid():
        # First generate attachment instance, to generate the target path.
        attachment = Attachment(content=content)
        attachment.save()

        try:
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

            try:
                content.html = None
                content.save()
            except:
                # The file is not saved until .save(commit=True).
                attachment.delete_file()
                raise
        except:
            attachment.delete()
            raise
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
