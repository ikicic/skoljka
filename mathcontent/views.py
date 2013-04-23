from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from skoljka.utils.decorators import response

from mathcontent.forms import AttachmentForm
from mathcontent.models import MathContent, Attachment
from mathcontent.utils import check_and_save_attachment

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

    return {
        'content': content,
        'form': form,
    }
