from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404

from permissions.constants import VIEW

from folder.models import Folder
from folder.utils import prepare_folder_menu

from functools import wraps

def folder_view(permission=None):
    """
        Decorator for folder views. Checks if the user has the access to the
        given folder and calls prepare_folder_menu.

        Expected function parameters:
            request, folder_id, (...)
        Decorated function parameters:
            request, folder, data, (...)

        Decorator arguments:
            permission - additionaly check given permission, default None
                (VIEW is checked anyway)

        Additional info added to the data dictionary:
            folder - the folder itself
            has_subfolders - boolean, True if given folder has any visible
                subfolder
            has_subfolders_strict = boolean, True if given folder has *any*
                subfolder
    """

    def decorator(func):
        def inner(request, folder_id=None, *args, **kwargs):
            if not folder_id:
                folder = Folder.objects.get(parent_id__isnull=True)
            else:
                folder = get_object_or_404(Folder, id=folder_id)

            # If type is VIEW, do not check twice.
            if permission and permission != VIEW and \
                    not folder.user_has_perm(request.user, permission):
                return HttpResponseForbidden('No permission for this action!')

            data = prepare_folder_menu([folder], request.user)
            # If you're the author, then you must have the access.
            # TODO: do this check only for VIEW, if not directly given
            # the permission?
            if folder.author_id != request.user.id and \
                    (not data or not data.get('folder_tree', None)):
                return HttpResponseForbidden('Not allowed to view this folder!')

            data['folder'] = folder
            try:
                has_subfolders = bool(data['folder_children'][data['folder'].id])
            except:
                has_subfolders = False
            data['has_subfolders'] = has_subfolders

            if has_subfolders:
                data['has_subfolders_strict'] = True
            else:
                # TODO: put in prepare_folder_menu?
                data['has_subfolders_strict'] = \
                    Folder.objects.filter(parent_id=folder.id).exists()

            return func(request, folder, data, *args, **kwargs)

        return wraps(func)(inner)
    return decorator
