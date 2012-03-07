from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponseBadRequest, HttpResponseRedirect

from permissions.constants import VIEW, EDIT

from folder.models import Folder
from task.models import Task

FOLDER_EDIT_LINK_CONTENT = ['Uredi', 'Zatvori']

@login_required
def select_task(request, task_id):
    folder = request.user.profile.selected_folder
    if not request.is_ajax() or folder is None:
        return HttpResponseBadRequest()
    if not folder.has_perm(request.user, EDIT):
        return HttpResponseForbidden('Not allowed to edit this folder.')
        
    task = get_object_or_404(Task, id=task_id)
    if not task.has_perm(request.user, VIEW):
        return HttpResponseForbidden('Not allowed to view this task.')
    
    if task in folder.tasks.all():
        folder.tasks.remove(task)
        response = '0'
    else:
        folder.tasks.add(task)
        response = '1'
        
    return HttpResponse(response)


@login_required
def select(request, id):
    folder = get_object_or_404(Folder, id=id)
    if not folder.has_perm(request.user, EDIT):
        return HttpResponseForbidden('Not allowed to edit this folder.')

    profile = request.user.profile    
    if profile.selected_folder == folder:
        profile.selected_folder = None
        response = 0
    else:
        profile.selected_folder = folder
        response = 1
        
    profile.save()
    #return HttpResponse(FOLDER_EDIT_LINK_CONTENT[response])
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def detail_by_id(request, id):
    folder = get_object_or_404(Folder, id=id)
    return HttpResponseRedirect('/folder/' + folder.get_full_path())


def view(request, path=u''):
    # moze li se hardkodirati dobivanje root-a?
    folder = get_object_or_404(Folder, parent__isnull=True)
    
    P = filter(None, path.split('/'))
    data = folder.get_template_data_from_path(P, u'', 0, request.user)
    if not data:
        raise Http404

    data['path'] = path + '/' if path else ''
    data['tasks'] = data['tasks'].select_related('author')
    if 'folder' in data and data['folder'].has_perm(request.user, EDIT):
        data['edit_link'] = FOLDER_EDIT_LINK_CONTENT[1 if request.user.get_profile().selected_folder == data['folder'] else 0]
    
    return render_to_response('folder_detail.html', 
            data,
        context_instance=RequestContext(request))
