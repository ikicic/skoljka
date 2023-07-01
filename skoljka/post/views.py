import sys

from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext

from skoljka.activity import action as _action
from skoljka.mathcontent.forms import MathContentForm
from skoljka.post.models import Post
from skoljka.utils.decorators import require


# TODO: bad request
@login_required
@require(post=['post_reply_id', 'post_redirect', 'object_id', 'content_type_id'])
def add_post(request):
    reply_to_id = request.POST['post_reply_id']
    reply_to = (
        None
        if not reply_to_id
        else get_object_or_404(Post.objects.select_related('author'), pk=reply_to_id)
    )

    math_content_form = MathContentForm(request.POST)
    if math_content_form.is_valid():
        content_type = get_object_or_404(
            ContentType, pk=request.POST['content_type_id']
        )
        try:
            object = content_type.get_object_for_this_type(pk=request.POST['object_id'])
        except:
            raise Http404('Object does not exist.')

        if hasattr(object, 'can_send_post'):
            if not object.can_send_post(request.user):
                return HttpResponseForbidden(
                    "You are not allowed to send messages to this object!"
                )

        object_author = getattr(object, 'author', None)
        object_author_id = None
        object_author_group = None
        if object_author:
            object_author_id = object_author.id
            try:
                object_author_group = Group.objects.get(name=object_author.username)
            except Group.DoesNotExist:
                pass
                # TODO: report error

        content = math_content_form.save()
        post = Post.objects.create(
            content_object=object,
            author=request.user,
            last_edit_by=request.user,
            content=content,
        )

        if reply_to:
            try:
                reply_to_author_group = Group.objects.get(name=reply_to.author.username)
            except Group.DoesNotExist:
                pass
                # TODO: report error
        else:
            reply_to_author_group = None

        _action.add(
            request.user,
            _action.POST_SEND,
            action_object=post,
            target=object,
            group=reply_to_author_group,
        )

    return HttpResponseRedirect(request.POST['post_redirect'])


@login_required
def edit_post(request, post_id=None):
    post = get_object_or_404(Post, pk=post_id)
    if not post.can_edit(request.user):
        return HttpResponseForbidden('Not allowed to edit this post.')

    if request.method == 'POST':
        math_content_form = MathContentForm(request.POST, instance=post.content)
        if math_content_form.is_valid():
            content = math_content_form.save()
            post.last_edit_by = request.user
            post.save()
            return HttpResponseRedirect(request.POST.get('next', '/'))

    return render_to_response(
        'post_edit.html',
        {
            'next': request.GET.get('next', '/'),
            'math_content_form': MathContentForm(instance=post.content),
            'post': post,
        },
        context_instance=RequestContext(request),
    )
