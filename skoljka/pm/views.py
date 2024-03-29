from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import connection, transaction
from django.http import (
    Http404,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext

from skoljka.mathcontent.forms import MathContentForm
from skoljka.pm.forms import NewMessageForm
from skoljka.pm.models import MessageContent, MessageRecipient

# TODO: What if you are in a hidden group and sending a message to the group,
# and to someone outside the group?! Leaving the problem for now, but it
# should be fixed somehow.
# TODO: optimize

# subject and text are ignored if method is 'POST'
@login_required
def new(request, rec='', subject='', text=''):
    if request.method == 'POST':
        message_form = NewMessageForm(request.POST, user=request.user)
        content_form = MathContentForm(request.POST)
        if message_form.is_valid() and content_form.is_valid():
            content = content_form.save()
            message = message_form.save(commit=False)
            message.content = content
            message.author = request.user
            message.save()

            groups = message_form.cleaned_data['list']
            message.groups = groups

            group_ids = ','.join([str(x.id) for x in groups])
            query1 = (
                'INSERT INTO pm_messagerecipient (recipient_id, message_id, deleted, `read`)'
                ' SELECT DISTINCT B.user_id, %d, 0, 0 FROM auth_group AS A'
                ' INNER JOIN auth_user_groups AS B ON (A.id = B.group_id)'
                ' WHERE A.id IN (%s);' % (message.id, group_ids)
            )
            query2 = (
                'UPDATE userprofile_userprofile AS C'
                ' INNER JOIN auth_user_groups AS B ON (B.user_id = C.user_id)'
                ' INNER JOIN auth_group AS A ON (A.id = B.group_id)'
                ' SET C.unread_pms = C.unread_pms + 1'
                ' WHERE A.id IN (%s) AND C.user_id != %d;'
                % (group_ids, request.user.id)
            )
            cursor = connection.cursor()
            cursor.execute(query1)
            cursor.execute(query2)
            transaction.commit_unless_managed()

            # fix `read` for messages sent also to sender himself
            # or just delete this?
            MessageRecipient.objects.filter(
                recipient=request.user, message=message
            ).update(read=1)

            return HttpResponseRedirect('/pm/outbox/')
    else:
        message_form = NewMessageForm(
            initial={'list': rec, 'subject': subject}, user=request.user
        )
        content_form = MathContentForm(initial={'text': text})

    return render_to_response(
        'pm_new.html',
        {
            'forms': [message_form, content_form],
        },
        context_instance=RequestContext(request),
    )


@login_required
def pm_action(request, id):
    try:
        action = request.path.rsplit('/', 2)[-2]
    except IndexError:
        return HttpResponseBadRequest("Something's wrong with the url.")

    pm = get_object_or_404(MessageContent, id=id)

    # TODO: replace with get_object_or_none()
    try:
        link = MessageRecipient.objects.get(
            recipient=request.user, message=pm, deleted=False
        )
    except MessageRecipient.DoesNotExist:
        link = None

    if pm.author != request.user and link is None:
        return HttpResponseForbidden('This message was not sent to or by you.')

    if action == 'delete':
        if pm.author == request.user:
            pm.deleted_by_author = True
            pm.save()
        if link:
            link.deleted = True
            link.save()
        return HttpResponseRedirect(request.META['HTTP_REFERER'])
    elif action in ['reply', 'replyall']:
        subject = pm.subject if pm.subject.startswith('Re: ') else 'Re: ' + pm.subject
        text = "\n\n\n\nPoslao %s %s:[quote]%s[/quote]" % (
            pm.author.username,
            pm.date_created.strftime('%d. %m. %Y. u %H:%M'),
            pm.content.text,
        )

        if action == 'reply':
            group_names = pm.author.username
        else:
            G = pm.groups.values_list('id', 'name')
            groups = [name for id, name in G]  # noqa: F812

            # add author to the list if not already in some of the groups
            if not pm.author.groups.through.objects.filter(
                user=pm.author, group__in=[id for id, name in G]
            ).exists():
                groups.append(pm.author.username)
            if request.user.username in groups:
                groups.remove(request.user.username)
            group_names = ', '.join(groups)

        return new(request, rec=group_names, subject=subject, text=text)
    elif action == 'forward':
        subject = pm.subject if pm.subject.startswith('Fw: ') else 'Fw: ' + pm.subject
        group_names = ', '.join(
            ['<%s>' % x for x in pm.groups.values_list('name', flat=True)]
        )
        text = "\n\n\n\n[quote]Poslao/la <%s> dana %s za %s.\n\n%s[/quote]" % (
            pm.author.username,
            pm.date_created.strftime('%d. %m. %Y. u %H:%M'),
            group_names,
            pm.content.text,
        )

        return new(request, subject=subject, text=text)

    # if action type not recognized
    raise Http404


# TODO: optimizirati
@login_required
def inbox(request):
    # pm = request.user.messages.filter(messagerecipient__deleted=False) \
    #       .exclude(author=request.user)   \
    #       .select_related('author', 'content', 'messagerecipient').order_by('-id')
    pm = (
        MessageRecipient.objects.filter(recipient=request.user, deleted=False)
        .exclude(message__author=request.user)
        .select_related('message', 'message__author', 'message__content')
        .order_by('-message__id')
    )

    return render_to_response(
        'pm_inbox.html',
        {
            'pm': pm,
        },
        context_instance=RequestContext(request),
    )


# TODO: optimizirati
@login_required
def outbox(request):
    # pm = MessageContent.objects.filter(author=request.user).select_related().order_by('-id')
    pm = (
        request.user.my_messages.filter(deleted_by_author=False)
        .select_related('content')
        .order_by('-id')
    )

    return render_to_response(
        'pm_outbox.html', {'pm': pm}, context_instance=RequestContext(request)
    )


# treba li ovo, tj. zelimo li to uopce?
@login_required
def group_inbox(request, group_id=None):
    group = get_object_or_404(Group, pk=group_id)
    if (
        request.user != group.data.author
        and not request.user.groups.filter(id=group_id).exists()
    ):
        raise Http404

    # pm = MessageContent.objects.filter(groups=group).select_related('author', 'content').order_by('-id').distinct()
    pm = (
        MessageContent.groups.through.objects.filter(group=group)
        .select_related(
            'messagecontent', 'messagecontent__author', 'messagecontent__content'
        )
        .order_by('-id')
    )

    return render_to_response(
        'pm_inbox.html',
        {
            'pm': pm,
            'group': group,
        },
        context_instance=RequestContext(request),
    )
