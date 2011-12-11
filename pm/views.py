from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from pm.models import MessageRecipient, MessageContent
from pm.forms import NewMessageForm
from mathcontent.forms import MathContentForm

#TODO: optimizirati
@login_required
def new(request, rec=None):
    if request.method == 'POST':
        message_form = NewMessageForm(request.POST)
        content_form = MathContentForm(request.POST)
        if message_form.is_valid() and content_form.is_valid():
            content = content_form.save()
            message = message_form.save(commit=False)
            message.content = content
            message.author = request.user
            message.save()
            
            recipients = message_form.cleaned_data['list']

            for recipient in recipients:
                r = MessageRecipient(message=message, content_object=recipient)
                r.save()
                
            return HttpResponseRedirect('/pm/outbox/')
    else:
        message_form = NewMessageForm(initial={'list': rec})
        content_form = MathContentForm()
        
    return render_to_response('pm_new.html', {
            'forms': [message_form, content_form],
        }, context_instance=RequestContext(request))
    
        

#TODO: optimizirati
@login_required
def inbox(request):
    pm = MessageRecipient.objects.inbox(request.user).order_by('-id')
    return render_to_response('pm_inbox.html', {
            'pm': pm,
        }, context_instance=RequestContext(request))


#TODO: optimizirati        
@login_required
def outbox(request):
    pm = MessageContent.objects.filter(author=request.user).select_related().order_by('-id')
    return render_to_response('pm_outbox.html', {
            'pm': pm
        }, context_instance=RequestContext(request))


@login_required
def group_inbox(request, group_id=None):
    group = get_object_or_404(Group, pk=group_id)
    pm = MessageRecipient.objects.inbox(group).order_by('-id')
    return render_to_response('pm_inbox.html', {
            'pm': pm,
            'group': group,
        }, context_instance=RequestContext(request))
