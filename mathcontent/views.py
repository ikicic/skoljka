from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from mathcontent.forms import AttachmentForm
from mathcontent.models import MathContent, Attachment

@login_required
def delete_attachment(request, id):
    attachment = get_object_or_404(Attachment, id=id)
    
    # TODO: POST method!
    if not request.is_ajax():
        return HttpResponseBadRequest()
        
    # TODO: permissions!!
    attachment.file.delete()
    attachment.delete()
    
    return HttpResponse('OK')

@login_required
def edit_attachments(request, id):
    content = get_object_or_404(MathContent, id=id)
    
    if request.method == 'POST':
        form = AttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = Attachment(content=content)
            attachment.save()
            
            # moram ovako tako da bi se mogao generirati pravilan filename
            form = AttachmentForm(request.POST, request.FILES, instance=attachment)
            attachment = form.save()
            
            print attachment
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        form = AttachmentForm()
    
    return render_to_response('mathcontent_edit_attachments.html', {
                'content': content,
                'form': form,
            }, context_instance=RequestContext(request),
        )
