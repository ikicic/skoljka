from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponseBadRequest, HttpResponseRedirect

from permissions.constants import VIEW, EDIT, EDIT_PERMISSIONS
from permissions.models import ObjectPermission
from task.models import Task
from skoljka.utils.decorators import response

from folder.models import Folder
from folder.forms import FolderForm
from folder.utils import refresh_cache

@login_required
def select_task(request, task_id):
    folder = request.user.profile.selected_folder
    if not request.is_ajax() or folder is None:
        return HttpResponseBadRequest()
    if not folder.user_has_perm(request.user, EDIT):
        return HttpResponseForbidden('Not allowed to edit this folder.')

    task = get_object_or_404(Task, id=task_id)
    if not task.user_has_perm(request.user, VIEW):
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
    if not folder.user_has_perm(request.user, EDIT):
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
    return HttpResponseRedirect(folder.get_absolute_url())


@response('folder_detail.html')
def view(request, path=u''):
    # Nonempty path must include last /.
    if path and path[-1] != '/':
        return (request.path + '/', )   # redirect

    # Immediately reject double slash, to prevent huge amount of unnecessary
    # queries (note that one slash == one query).
    if '//' in path or len(path) > 0 and path[0] == '/':
        return 404

    # Find longest used path prefix. Note that if cache_path != path, it is
    # still possible for path to be valid (as the folder might have virtual
    # subfolders)
    folder = None
    index = len(path)
    while True:
        try:
            folder = Folder.objects.get(cache_path=path[:index + 1])
            break
        except Folder.DoesNotExist:
            pass

        index = path.rfind('/', 0, index)

    if not folder:
        # Root folder missing?
        raise Expection("No matching folder for path " + path)

    # Retrieve all necessary information
    data = folder.get_template_data_from_path(path, request.user)
    if not data:
        raise Http404

    # Some additional tuning
    data['tasks'] = data['tasks'].select_related('author')

    folder = data.get('folder')
    if folder and folder.user_has_perm(request.user, EDIT):
        data['edit_link'] = True
        if not data['tag_list']:
            data['select_link'] = True

    return data

@response('folder_new.html')
def new(request, folder_id=None):
    # Analogous to task.models.new

    if folder_id:
        folder = get_object_or_404(Folder, id=folder_id)
        edit = True
        old_parent_id = folder.parent_id
    else:
        folder = old_parent_id = None
        edit = False

    if request.method == 'POST':
        folder_form = FolderForm(request.POST, instance=folder, user=request.user)
        if folder_form.is_valid():
            folder = folder_form.save(commit=False)

            folder.slug = slugify(folder.name)

            if not edit:
                folder.author = request.user

            folder.save()

            # Refresh Folder cache.
            # TODO: Optimize, update only necessary folders.
            if old_parent_id != folder.parent_id:
                refresh_cache(Folder.objects.all())

            # Get new path
            folder = Folder.objects.get(id=folder.id)
            return HttpResponseRedirect(folder.get_absolute_url())
    else:
        folder_form = FolderForm(instance=folder, user=request.user)

    data = {
        'form': folder_form,
        'edit': edit,
        'folder': folder,
    }

    if edit:
        permissions = folder.get_user_permissions(request.user)

        if EDIT not in permissions:
            return ('/', )

        if EDIT_PERMISSIONS in permissions:
            data['can_edit_permissions'] = True
            data['content_type'] = ContentType.objects.get_for_model(Folder)


    return data
