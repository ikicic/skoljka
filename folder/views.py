from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect

from folder.models import Folder
from task.models import Task

FOLDER_EDIT_LINK_CONTENT = ['Uredi', 'Zatvori']

@login_required
def select_task(request, task_id):
    folder = request.user.profile.selected_folder
    if not request.is_ajax() or folder is None:
        return HttpResponseBadRequest()
    task = get_object_or_404(Task, id=task_id)
    
    if task in folder.tasks.all():
        folder.tasks.remove(task)
        response = '0'
    else:
        folder.tasks.add(task)
        response = '1'
        
    return HttpResponse(response)


@login_required
def select(request, id):
    if not request.is_ajax():
        return HttpResponseBadRequest()
    folder = get_object_or_404(Folder, id=id)

    profile = request.user.profile    
    if profile.selected_folder == folder:
        profile.selected_folder = None
        response = 0
    else:
        profile.selected_folder = folder
        response = 1
        
    profile.save()
    return HttpResponse(FOLDER_EDIT_LINK_CONTENT[response])


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
    if 'folder' in data and request.user.is_authenticated():
        data['edit_link'] = FOLDER_EDIT_LINK_CONTENT[1 if request.user.get_profile().selected_folder == data['folder'] else 0]
    
    return render_to_response('folder_detail.html', 
            data,
        context_instance=RequestContext(request))
