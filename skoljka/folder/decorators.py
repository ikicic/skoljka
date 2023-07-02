from functools import wraps

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404

from skoljka.folder.models import Folder
from skoljka.folder.utils import prepare_folder_menu
from skoljka.permissions.constants import VIEW


def folder_view(permission=VIEW):
    """
    Decorator for folder views. Checks if the user has the access to the
    given folder and calls prepare_folder_menu.

    Expected function parameters:
        request, folder_id, (...)
    Decorated function parameters:
        request, folder, data, (...)

    Decorator arguments:
        permission - permission to check

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

            # If type is VIEW, wait, do not call expensive .user_has_perm.
            if permission != VIEW:
                explicit = folder.user_has_perm(request.user, permission)
                if not explicit:
                    # Reject immediately, do not waste time
                    return HttpResponseForbidden("No permission for this action!")
            else:
                explicit = None

            data = prepare_folder_menu([folder], request.user)
            if not data or not data.get('folder_tree', None):
                # Even if you are not able to see the folder's ancestors,
                # you may still have explicit permission.
                # (for example, if you are the author, or the author gave you
                # the permission to update/view the folder)

                # Note: This results in a small security problem. The URL,
                # i.e. path of the folder contains short names of its ancestors.
                if permission == VIEW:
                    # ok, now check permissions... (can prepare_folder_menu
                    # give me this same information?)
                    explicit = folder.user_has_perm(request.user, permission)
                if not explicit:
                    return HttpResponseForbidden("No permission for this action!")

            data['folder'] = folder
            try:
                has_subfolders = bool(data['folder_children'][data['folder'].id])
            except:  # noqa: E722
                has_subfolders = False
            data['has_subfolders'] = has_subfolders

            if has_subfolders:
                data['has_subfolders_strict'] = True
            else:
                # TODO: put in prepare_folder_menu?
                data['has_subfolders_strict'] = Folder.objects.filter(
                    parent_id=folder.id
                ).exists()

            return func(request, folder, data, *args, **kwargs)

        return wraps(func)(inner)

    return decorator
