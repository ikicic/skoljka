from __future__ import print_function

import re

from django.conf import settings
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponsePermanentRedirect,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.template.defaultfilters import slugify

from skoljka.folder.decorators import folder_view
from skoljka.folder.forms import FolderAdvancedCreateForm, FolderForm
from skoljka.folder.models import (
    FOLDER_NAMESPACE_FORMAT,
    FOLDER_TASKS_DB_TABLE,
    Folder,
    FolderTask,
)
from skoljka.folder.utils import (
    add_or_remove_folder_task,
    get_folder_descendant_ids,
    get_visible_folder_tree,
    prepare_folder_menu,
    refresh_path_cache,
)
from skoljka.permissions.constants import DELETE, EDIT, EDIT_PERMISSIONS, VIEW
from skoljka.permissions.models import ObjectPermission
from skoljka.tags.utils import set_tags
from skoljka.task.models import Task
from skoljka.utils import get_referrer_path, ncache
from skoljka.utils.decorators import response


# TODO: check ancestor VIEW permissions?
def redirect_by_path(request, path):
    migrations = [('', '')] + settings.FOLDER_PATH_MIGRATIONS

    folder = None
    for old, new in migrations:
        new_path = path.replace(old, new)
        if new_path == path and old and new:
            continue
        folder = list(Folder.objects.filter(cache_path=new_path))
        if folder:
            folder = folder[0]
            break

    if not folder or not folder.user_has_perm(request.user, VIEW):
        raise Http404
    url = folder.get_absolute_url()
    parameters = request.GET.urlencode()
    if parameters:
        url += '?' + parameters
    return HttpResponsePermanentRedirect(url)


@folder_view(permission=DELETE)
@response('folder_delete.html')
def delete(request, folder, data):
    if not data['has_subfolders_strict'] and request.POST:
        if 'confirm' in request.POST:
            parent = folder.parent
            folder.delete()
            return (parent.get_absolute_url(),)

    return data


def _edit_tasks_tasks(folder, user):
    return (
        folder.tasks.for_user(user, VIEW)
        .extra(
            select={'position': FOLDER_TASKS_DB_TABLE + '.position'},
            order_by=['position'],
        )
        .distinct()
    )


@folder_view(permission=EDIT)
@response('folder_edit_tasks.html')
def edit_tasks(request, folder, data):
    if not folder.editable:
        return 403

    # Not able to use FolderTask.objects.filter, as it is still required to
    # check permissions...

    invalid = set()
    unknown = set()
    updated = set()

    if request.method == 'POST':
        tasks = _edit_tasks_tasks(folder, request.user)
        task_info = dict(tasks.values_list('id', 'position'))
        for key, value in request.POST.iteritems():
            if not re.match('^position-\d+$', key):
                continue

            id = int(key[9:])
            if id not in task_info:
                unknown.add(id)
            elif not value.isdigit():
                invalid.add(id)
            else:
                value = int(value)
                if value != task_info[id]:
                    FolderTask.objects.filter(folder=folder, task_id=id).update(
                        position=value
                    )
                    updated.add(id)

    tasks = _edit_tasks_tasks(folder, request.user)

    data.update(
        {
            'tasks': tasks,
            'invalid': invalid,
            'unknown': unknown,
            'updated': updated,
        }
    )

    return data


# TODO: check ancestor VIEW permissions?
@login_required
def select_task(request, task_id):
    folder = request.user.profile.selected_folder
    if not request.is_ajax() or folder is None:
        return HttpResponseBadRequest()
    if not folder.editable or not folder.user_has_perm(request.user, EDIT):
        return "Not allowed to edit this folder."

    task = get_object_or_404(Task, id=task_id)
    if not task.user_has_perm(request.user, VIEW):
        return "Not allowed to view this task."

    add = request.POST['checked'] == 'true'
    error = add_or_remove_folder_task(folder.id, task.id, add)
    if error:
        return HttpResponseBadRequest(error)

    return HttpResponse('1' if add else '0')


# TODO: check ancestor VIEW permissions?
@login_required
def select(request, id):
    folder = get_object_or_404(Folder, id=id)
    if not folder.user_has_perm(request.user, EDIT):
        return HttpResponseForbidden("Not allowed to edit this folder.")

    profile = request.user.profile
    if profile.selected_folder == folder:
        profile.selected_folder = None
        response = 0
    else:
        profile.selected_folder = folder
        response = 1

    profile.save()
    # return HttpResponse(FOLDER_EDIT_LINK_CONTENT[response])
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


@response('folder_list.html')
@login_required
def folder_my(request):
    """
    List all folders created by the user.
    """
    folders = list(Folder.objects.filter(author_id=request.user.id))
    if not folders:
        return {}

    original_ids = set(x.id for x in folders)

    data = get_visible_folder_tree(folders, request.user) or {}
    ancestor_ids = data.get('ancestor_ids', [])
    sorted_folders = data.get('sorted_folders', [])

    accessible_ids = set()

    folders_html = []
    for x in sorted_folders:
        if x.id in original_ids:
            html = x._html_menu_item(
                True,
                x._depth,
                None,
                cls='folder-list-my',
                extra='<a href="/folder/{}/edit/" class="folder-list-my-edit"'
                ' title="Uredi"> <i class="icon-edit"></i></a>'.format(x.id),
            )
            accessible_ids.add(x.id)
        else:
            html = x._html_menu_item(x.id in ancestor_ids, x._depth, None)
        folders_html.append(html)

    return {
        'folders_html': u''.join(folders_html),
        'inaccessible_folders': [
            x for x in folders if x.parent_id and x.id not in accessible_ids
        ],
    }


@folder_view()
@response('folder_detail.html')
def view(request, folder, data, path=u''):
    if path != folder.cache_path:
        # Redirect to the correct URL. E.g. force / at the end etc.
        return (folder.get_absolute_url(),)

    data.update(folder.get_details(request.user))

    # Some additional tuning
    data['dont_hide_sidebar'] = True
    data['tasks'] = data['tasks'].select_related('author')

    if folder.editable and folder.user_has_perm(request.user, EDIT):
        data['edit_link'] = True
        if not data['tag_list']:
            data['select_link'] = True
        if request.user.get_profile().selected_folder == folder:
            data['this_folder_selected'] = True

    return data


@login_required
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

    data = {}

    initial_parent_id = None

    if edit:
        if not folder.editable:
            return response.FORBIDDEN

        permissions = folder.get_user_permissions(request.user)

        if EDIT not in permissions:
            return response.FORBIDDEN

        if EDIT_PERMISSIONS in permissions:
            data['can_edit_permissions'] = True
            data['content_type'] = ContentType.objects.get_for_model(Folder)

        data['children'] = children = list(
            Folder.objects.for_user(request.user, VIEW)
            .filter(parent=folder)
            .order_by('parent_index')
            .distinct()
        )

        data['has_subfolders_strict'] = Folder.objects.filter(
            parent_id=folder_id
        ).exists()
    else:
        referrer = get_referrer_path(request)
        if referrer and referrer.startswith('/folder/'):
            try:
                initial_parent_id = int(referrer[8 : referrer.find('/', 8)])
            except:
                pass

    if request.method == 'POST':
        folder_form = FolderForm(request.POST, instance=folder, user=request.user)
        if folder_form.is_valid():
            folder = folder_form.save(commit=False)

            # TODO: Make a util function for creating Folder instances, to be
            # able to create tests easier.

            # If user can't edit short name, copy full name.
            if 'short_name' not in folder_form.fields:
                folder.short_name = folder.name

            if not edit:
                folder.author = request.user
            else:
                for x in children:
                    parent_index = request.POST.get('child-{}'.format(x.id))
                    parent_index = int(parent_index)
                    if parent_index is not None and x.parent_index != parent_index:
                        x.parent_index = parent_index
                        x.save()

                # Update order...
                children.sort(key=lambda x: x.parent_index)

                # If editing, refresh immediately before saving.
                # Do not call folder_form.save_m2m()!
                folder._no_save = True
                set_tags(folder, folder_form.cleaned_data['tags'])

            folder.save()

            if not edit:
                # If new, first save folder (and define ID), and then save tags.
                set_tags(folder, folder_form.cleaned_data['tags'])

            # Refresh Folder cache.
            if old_parent_id != folder.parent_id:
                # The only folders that have to be refreshed are those in
                # the folder's subtree, together with folder itself.
                descendant_ids = get_folder_descendant_ids(folder.id)
                descendant_ids.append(folder.id)
                # refresh_path_cache also requires ancestors. Following code
                # works, because you can't move a folder into its child folder.
                descendant_ids.extend(
                    [int(x) for x in folder.parent.cache_ancestor_ids.split(',') if x]
                )
                descendant_ids.append(folder.parent_id)
                refresh_path_cache(Folder.objects.filter(id__in=descendant_ids))

            if not edit:
                return ('/folder/{}/edit/'.format(folder.id),)
            # return HttpResponseRedirect(folder.get_absolute_url())
    else:
        folder_form = FolderForm(
            instance=folder, user=request.user, initial_parent_id=initial_parent_id
        )

        # If parent given and acceptable, show menu. (new mode)
        initial_parent = getattr(folder_form, 'initial_parent', None)
        if initial_parent:
            data.update(prepare_folder_menu([initial_parent], request.user))

    if edit:
        data.update(prepare_folder_menu([folder], request.user))
        data['folder'] = folder

    data['form'] = folder_form
    data['edit'] = edit

    if request.user.has_perm('folder.advanced_create'):
        data['advanced_create_permission'] = True

    return data


def _dict_to_object(d):
    class Struct(object):
        def __init__(self, d):
            self.__dict__.update(d)

    return Struct(d)


def _create_folders(author, parent, structure, p):
    vars = {'p': p}

    level, separator, rest = structure.partition('|')
    rest = rest.strip()

    # Split the level description into lines, remove trailing and leading
    # whitespaces, and remove empty lines
    lines = filter(None, [x.strip() for x in level.strip().split('\n')])

    # Child format defined in the first line
    # Format: var_name1/var_name2/.../var_nameN
    var_names = [x.strip() for x in lines[0].split('/')]

    # Evaluate variables in specified order, don't shuffle them!
    var_formats = []

    # List of children tuples
    children = []

    # Skip first line!
    for x in lines[1:]:
        left, separator, right = x.partition('=')

        if separator:
            # Variable definition: var_name=this is a example number {x}
            var_formats.append((left, right))
        elif left[0] == '%':
            # Special command
            if left.startswith('%RANGE'):
                # E.g. %RANGE 2012, 1996
                # --> Adds children: 2012, 2011, ..., 1997, 1996
                a, b = [int(x) for x in left[6:].split(',')]
                r = range(a, b + 1) if a <= b else range(a, b - 1, -1)
                children.extend([str(x) for x in r])
            else:
                raise Exception("Nepoznata naredba: " + left)
        else:
            # Child definition: var_value1/var_value2/.../var_valueN
            children.append(left)

    created = 0
    existing = 0
    for index, x in enumerate(children):
        # Update vars with child var values. (values are stripped!)
        vars.update({k: v.strip() for k, v in zip(var_names, x.split('/'))})

        # Update additional vars
        for var in var_formats:
            # Note we are using same dictionary that is being updated, that's
            # why order matters
            vars[var[0]] = var[1].format(**vars)

        try:
            # Check if folder with the same name, short name and parent exists.
            folder = Folder.objects.get(
                parent=parent, name=vars['name'], short_name=vars['short']
            )
            existing += 1
        except:
            # If not, create new folder.
            folder = Folder(
                author=author,
                parent=parent,
                parent_index=index,
                hidden=False,
                editable=False,
                name=vars['name'],
                short_name=vars['short'],
            )
            folder.save()
            created += 1

        # Note that the object has to exist to use this!
        set_tags(folder, vars['tags'])
        # TODO: call folder._refresh_cache_tags() on change signal.

        # Call recursion if there is any level left
        if rest:
            # Note that parent changed!
            _c, _e = _create_folders(author, folder, rest, _dict_to_object(vars))
            created += _c
            existing += _e

    return created, existing


# stored as object_repr in django_admin_log
ADVANCED_NEW_OBJECT_REPR = u'<advanced new>'


@permission_required('folder.advanced_create')
@response('folder_advanced_new.html')
def advanced_new(request):
    """
    Create folders defined by structure and the parent.
    Existing folder (folders with matching short, full name and parent)
    will be used instead of creating new ones.

    Structure format:
        level1 [ | level2 [ | level3 ... ] ]
    Level format:
        i) variable names
        ii) list of child folders - variable values
        iii) format of additional variables

    Or, more detailed:
        var_name1/var_name2/...var_nameN

        child1_var_value1/child1_var_value2/.../child1_var_valueN
        ...
        childM_var_value1/childM_var_value2/.../childM_var_valueN

        some_var={var_nameX} some text, {var_nameX}
        other_var={var_nameY} {var_nameZ} text text

    Also, to access variables from previous levels, use 'p.' prefix. E.g:
        name={p.competition_name} {year}

    There are three variables that has to be set (as i+ii or iii):
        name = full name of the folder
        short = shown in menu
        tags = tag filters for the folder
    If any of these variables are missing, parser will throw an expection.

    Special functions:
        Instead of listing dozens of years (ii part), you can use this
        helper function:
            %RANGE a, b
        which acts like numbers from a to b, inclusive (works both asc/desc)



    Real example:
        name/tags

        International Mathematical Olympiad/imo
        International Mathematical Olympiad - Shortlist/shortlist

        short={name}

        |

        year

        %RANGE 2011, 1959

        name={p.name} {year}
        short={year}
        tags={p.tags},{year}
    """

    content_type = ContentType.objects.get_for_model(Folder)

    created = 0
    existing = 0
    if request.POST:
        form = FolderAdvancedCreateForm(request.user, request.POST)
        if form.is_valid():
            parent = form.cleaned_data['parent']
            structure = form.cleaned_data['structure']

            # Use admin log to save structure for future changes
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=content_type.id,
                object_id=parent.id,
                object_repr=ADVANCED_NEW_OBJECT_REPR,
                action_flag=CHANGE,
                change_message=structure,
            )

            print("Creating folders...")
            created, existing = _create_folders(request.user, parent, structure, None)

            # print 'Refreshing folder cache...'
            # refresh_cache_fields(Folder.objects.all())

    else:
        form = FolderAdvancedCreateForm(request.user)

    structure_history = LogEntry.objects.filter(
        content_type=content_type, object_repr=ADVANCED_NEW_OBJECT_REPR
    )
    history_array = [
        {'title': x.action_time, 'content': x.change_message} for x in structure_history
    ]

    return {
        'form': form,
        'created_folder_count': created,
        'existing_folder_count': existing,
        'history_array': history_array,
    }
