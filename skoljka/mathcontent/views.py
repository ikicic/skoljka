from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from skoljka.task.utils import get_task_folder_data
from skoljka.utils.decorators import response

from skoljka.mathcontent.forms import AttachmentForm
from skoljka.mathcontent.models import MathContent, Attachment
from skoljka.mathcontent.utils import \
        check_edit_attachments_permissions, check_and_save_attachment

@login_required
@response('mathcontent_edit_attachments.html')
def edit_attachments(request, id):
    """List attachments, add new and delete existing ones."""
    content = get_object_or_404(MathContent, id=id)
    result = check_edit_attachments_permissions(request.user, content)
    if not result.allowed:
        return 404  # Could be 403 in some cases.

    if request.method == 'POST':
        if 'delete_attachment_id' in request.POST:
            try:
                attachment = Attachment.objects.get(
                        id=request.POST['delete_attachment_id'])
            except Attachment.DoesNotExist:
                return 403  # Always 403.
            if attachment.content_id != content.id:
                return 403  # Always 403.

            attachment.content = content  # Reuse.
            attachment.delete_file()
            attachment.delete()
            content.html = None
            content.save()

            # Redirect to avoid form resubmission.
            return (content.get_edit_attachments_url(),)

        attachment, form = check_and_save_attachment(request, content)
        if attachment is not None:
            # Redirect to avoid form resubmission.
            return (content.get_edit_attachments_url(),)
    else:
        form = AttachmentForm()

    assert result.task is not None, \
           "assuming for now only Task MathContents can have attachments"
    data = {
        'content': content,
        'form': form,
        'task': result.task,
    }
    data.update(get_task_folder_data(result.task, request.user))

    return data
