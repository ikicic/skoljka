from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from actstream import action

from mathcontent.forms import MathContentForm
from post.models import Post

import sys

#TODO: sto ako forma nije valid?
@login_required
def add_post(request):
    if request.method != 'POST':
        raise Http404
    if any(x not in request.POST for x in ['post_redirect', 'object_id', 'content_type_id']):
        raise Http404

    math_content_form = MathContentForm(request.POST)
    if math_content_form.is_valid():
        content = math_content_form.save()
        post = Post.objects.create(
                object_id = request.POST['object_id'],
                content_type = ContentType.objects.get(pk=request.POST['content_type_id']),
                author = request.user,
                last_edit_by = request.user,
                content = content
            )
        post.save()
    
    return HttpResponseRedirect(request.POST['post_redirect'])


@login_required
def edit_post(request, post_id=None):
    post = get_object_or_404(Post, pk=post_id)
    if request.method == 'POST':
        math_content_form = MathContentForm(request.POST, instance=post.content)
        if math_content_form.is_valid():
            content = math_content_form.save()
            post.last_edit_by = request.user
            post.save()
            return HttpResponseRedirect(request.POST.get('next', '/'))

    return render_to_response('post_edit.html', {
                'next': request.GET.get('next', '/'),
                'math_content_form': MathContentForm(instance=post.content),
                'post': post,
            }, context_instance=RequestContext(request),
        )
