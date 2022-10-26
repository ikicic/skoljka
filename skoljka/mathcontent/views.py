from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from skoljka.permissions.constants import EDIT
from skoljka.task.models import Task
from skoljka.task.utils import get_task_folder_data
from skoljka.utils.decorators import response

from skoljka.mathcontent.forms import AttachmentForm
from skoljka.mathcontent.models import MathContent, Attachment
from skoljka.mathcontent.utils import check_and_save_attachment

# TODO: ajax decorator etc. refactor
@login_required
def delete_attachment(request, id):
    attachment = get_object_or_404(Attachment.objects.select_related('content'), id=id)

    # TODO: POST method!
    if not request.is_ajax():
        return HttpResponseBadRequest()

    # refresh HTML cache
    attachment.content.html = None
    attachment.content.save()

    # TODO: permissions!!
    attachment.file.delete()
    attachment.delete()


    return HttpResponse('OK')

@login_required
@response('mathcontent_edit_attachments.html')
def edit_attachments(request, id):
    content = get_object_or_404(MathContent, id=id)

    if request.method == 'POST':
        attachment, form = check_and_save_attachment(request, content)
    else:
        form = AttachmentForm()

    data = {
        'content': content,
        'form': form,
    }

    # Type-specific tuning and permissions:
    try:
        task = Task.objects.get(content_id=id)
        if not task.is_allowed_to_edit(request.user):
            return 403
        data['task'] = task
        data.update(get_task_folder_data(task, request.user))
    except Task.DoesNotExist:
        # Only Task's MathContent can have attachments!
        return 404

    return data
