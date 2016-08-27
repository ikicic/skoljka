from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Min
from django.http import Http404, HttpResponse, HttpResponseRedirect, \
        HttpResponseServerError
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string

from pagination.paginator import InfinitePaginator

from activity import action as _action
from base.utils import can_edit_featured_lectures
from folder.models import Folder, FolderTask
from folder.utils import invalidate_cache_for_folders, \
        invalidate_folder_cache_for_task
from mathcontent.forms import AttachmentForm, MathContentForm
from mathcontent.latex import latex_escape
from mathcontent.models import MathContent, Attachment
from mathcontent.utils import check_and_save_attachment, convert_to_latex, \
        create_file_thumbnail, ThumbnailRenderingException
from permissions.constants import EDIT, VIEW, EDIT_PERMISSIONS, VIEW_SOLUTIONS
from permissions.models import ObjectPermission
from solution.models import Solution, SolutionStatus
from tags.utils import set_tags, split_tags
from usergroup.forms import GroupEntryForm

from skoljka.libs.decorators import response
from skoljka.libs.string_operations import media_path_to_url
from skoljka.libs.timeout import run_command

from task.models import SimilarTask, Task, TaskBulkTemplate
from task.forms import TaskAdvancedForm, TaskBulkTemplateForm, TaskExportForm, \
        TaskFileForm, TaskForm, TaskJSONForm, TaskLectureForm, \
        EXPORT_FORMAT_CHOICES
from task.utils import check_prerequisites_for_task, \
        check_prerequisites_for_tasks, create_tasks_from_json, \
        get_task_folder_data

import codecs, datetime, hashlib, json, os, sys, traceback, zipfile
import django_sorting

# TODO: promijeniti nacin na koji se Task i MathContent generiraju.
# vrijednosti koje ne ovise o samom formatu se direktno trebaju
# postaviti na vrijednosti iz forme.


@response('task_json_new.html')
@permission_required('task.add_advanced')
def json_new(request):
    message = ''
    if request.method == 'POST':
        form = TaskJSONForm(request.POST)
        if form.is_valid():
            description = json.loads(form.cleaned_data['description'])
            try:
                tasks = create_tasks_from_json(description)
                message = "Created {} task(s).".format(len(tasks))
            except Exception as e:
                message = e.message
    else:
        form = TaskJSONForm()

    return {'form': form, 'message': message}


@login_required
@response('task_bulk_new_success.html')
def bulk_new_success(request):
    """Redirected to after successful bulk add."""
    return {'total': request.GET.get('total')}


@permission_required('task.can_bulk_add')
@response('task_bulk_new.html')
def bulk_new(request, template_id=None):
    template = None
    if template_id:
        template = get_object_or_404(TaskBulkTemplate, id=template_id)
    edit = template is not None
    error = None

    if request.method == 'POST':
        if 'step' not in request.POST:
            return 400
        form = TaskBulkTemplateForm(request.POST, instance=template,
                user=request.user)
        if form.is_valid():
            step = request.POST['step']
            jsons = [x.json for x in form.task_infos]
            if step == 'final' and request.POST.get('action') == 'create':
                try:
                    tasks = create_tasks_from_json(jsons)
                except Exception as e:
                    error = e.message

                if error is None:
                    template = form.save(commit=False)
                    template.author = request.user
                    template.save()
                    total = len(tasks)
                    # return ('/task/new/bulk/success/?total=' + str(total), )
            if step == 'second' and jsons:
                json_dump = json.dumps(jsons, indent=2, sort_keys=True)
                return ('task_bulk_new_2nd.html', {
                    'form': form,
                    'task_infos': form.task_infos,
                    'json_dump': json_dump,
                })
    else:
        form = TaskBulkTemplateForm(instance=template, user=request.user)

    history = list(TaskBulkTemplate.objects.for_user(request.user, VIEW) \
            .order_by('id').distinct())
    history = [{
            'title': u"{} ({})".format(x.name, x.last_edit_date),
            'content': x.source_code,
        } for x in history]

    return {
        'error': error,
        'form': form,
        'task_infos': form.task_infos,
        'history': history,
    }


def new_file(request):
    return new(request, is_file=True)


def new_lecture(request):
    return new(request, is_file=True, is_lecture=True)


@login_required
@response('task_new.html')
def new(request, task_id=None, is_file=None, is_lecture=None):
    """
        New Task and Edit Task
        + New TaskFile and Edit TaskFile
    """
    content_type = ContentType.objects.get_for_model(Task)

    if task_id:
        task = get_object_or_404(Task.objects.select_related('content'), pk=task_id)
        perm = task.get_user_permissions(request.user)
        if EDIT not in perm:
            return 403
        math_content = task.content
        edit = True
        is_file = task.is_file()
        is_lecture = task.is_lecture
    else:
        perm = []
        task = math_content = None
        edit = False

    # Make sure each lecture is a file.
    assert is_lecture and is_file or not is_lecture

    form_class = TaskLectureForm if is_lecture \
            else (TaskFileForm if is_file else TaskForm)
    math_content_label = 'Opis' if is_file else None    # else default

    if request.method == 'POST':
        old_hidden = getattr(task, 'hidden', -1)
        old_solvable = getattr(task, 'solvable', -1)

        # Files can have blank description (i.e. math content)
        task_form = form_class(request.POST, instance=task, user=request.user)
        math_content_form = MathContentForm(request.POST, instance=math_content,
            blank=is_file, label=math_content_label, auto_preview=False)
        attachment_form = is_file and not edit \
            and AttachmentForm(request.POST, request.FILES)

        if task_form.is_valid() and math_content_form.is_valid()    \
                and (not attachment_form or attachment_form.is_valid()):

            task = task_form.save(commit=False)
            math_content = math_content_form.save()

            if not edit:
                if attachment_form:
                    attachment, attachment_form = check_and_save_attachment(
                        request, math_content)
                    task.file_attachment = attachment   # This is a file.
                    path = attachment.get_full_path_and_filename()
                    try:
                        thumbnail_path = create_file_thumbnail(path)
                        task.cache_file_attachment_thumbnail_url = \
                                media_path_to_url(thumbnail_path)
                    except ThumbnailRenderingException:
                        pass

                    # Immediately remember file url, so that we don't have to
                    # access Attachment table to show the link.
                    task.cache_file_attachment_url = attachment.get_url()
                else:
                    task.file_attachment = None         # This is a task.

            if is_file:
                task.cache_file_attachment_url = task.file_attachment.get_url()
            if not edit:
                task.author = request.user
            task.content = math_content

            task.save()
            # Do not call task_form.save_m2m()!
            set_tags(task, task_form.cleaned_data['tags'])

            # TODO: signals!
            if not edit or old_hidden != task.hidden    \
                    or old_solvable != task.solvable:   \
                invalidate_folder_cache_for_task(task)

            # send action if creating a new nonhidden task
            if not edit:
                # TODO: signals!
                type = _action.LECTURE_ADD if is_lecture \
                        else (_action.FILE_ADD if is_file else _action.TASK_ADD)

                _action.add(request.user, type,
                    action_object=task, target=task)

            # TODO: izbrisati task_new_finish.html i url
            #return HttpResponseRedirect('/task/%d/' % task.id if edit else '/task/new/finish/')
            return HttpResponseRedirect(task.get_absolute_url())
    else:
        task_form = form_class(instance=task)
        math_content_form = MathContentForm(instance=math_content,
            blank=is_file, label=math_content_label, auto_preview=False)
        attachment_form = is_file and not edit and AttachmentForm()

    forms = [task_form, math_content_form]
    if attachment_form:
        forms.append(attachment_form)

    data = get_task_folder_data(task, request.user) if task else {}

    data.update({
        'action_url': request.path,
        'bulk_add_url': '/task/new/bulk/',
        'can_edit_permissions': EDIT_PERMISSIONS in perm,
        'content_type': content_type,
        'edit': edit,
        'forms': forms,
        'is_file': is_file,
        'is_lecture': is_lecture,
        'lectures_folder_url': settings.LECTURES_FOLDER_URL,
        'task_name': task.name if task else None,  # Convenience.
        'task': task,
    })

    return data


@response('task_lectures_list.html')
def lectures_list(request):
    lectures = Task.objects.for_user(request.user, VIEW) \
            .filter(is_lecture=True).distinct()
    return {'lectures': lectures}


def lectures_as_list(request):
    return task_list(request, only_lectures=True)


@response('task_list.html')
def task_list(request, user_id=None, only_lectures=False):
    tasks = Task.objects.for_user(request.user, VIEW)
    if only_lectures:
        tasks = tasks.filter(is_lecture=True)
    tasks = tasks.select_related('content').distinct()
    # treba mi LEFT JOIN ON (task_task.id = solution_solution.task_id AND solution_solution.author_id = ##)
    # sada se umjesto toga koristi .cache_task_info()
    # (slicno za tag-ove)

    if user_id:
        tasks = tasks.filter(author_id=user_id)

    return {
        'can_bulk_add': request.user.has_perm('task.can_bulk_add'),
        'only_lectures': only_lectures,
        'tasks': tasks,
    }


@response('task_detail.html')
def detail(request, id):
    task = get_object_or_404(Task, id=id)

    perm = task.get_user_permissions(request.user)
    if VIEW not in perm:
        return (403, 'Not allowed to view this task!')
    if not check_prerequisites_for_task(task, request.user, perm):
        return (403, 'Prerequisites not met, not allowed to view the task!')

    # Remember my solution.
    try:
        solution = Solution.objects.get(
                author_id=request.user.id, task_id=task.id)
    except:
        solution = None
    task.cache_solution = solution

    data = {
        'task': task,
        'can_edit': EDIT in perm,
        'solution': solution,
    }

    featured_folder_id = getattr(settings, 'FEATURED_LECTURES_FOLDER_ID', None)
    if task.is_lecture and featured_folder_id and \
            can_edit_featured_lectures(request.user):
        # The case where task is hidden is handled in the template.
        data['can_select_as_featured'] = True
        data['is_featured'] = FolderTask.objects \
                .filter(folder_id=featured_folder_id, task_id=id).exists()

    folder_data = get_task_folder_data(task, request.user)
    if folder_data:
        data.update(folder_data)

    return data

@response('task_similar.html')
def similar(request, task_id):
    # SPEED: read main task together with the rest
    task = get_object_or_404(Task, pk=task_id)

    sorted_tasks = dict(SimilarTask.objects \
            .filter(task_id=task_id)[:50].values_list('similar_id', 'score'))

    if request.user.is_authenticated():
        solutions = Solution.objects \
                .filter(task__similar_backward=task, author=request.user) \
                .exclude(status=SolutionStatus.BLANK) \
                .only('status', 'correctness_avg', 'task')
        for s in solutions:
            p = 1.0
            if s.is_todo(): p = 0.5
            elif s.is_as_solved(): p = 0.3
            elif s.is_submitted() and s.is_correct(): p = 0.2

            sorted_tasks[s.task_id] *= p

    sorted_tasks = sorted(
            [(p, id) for id, p in sorted_tasks.iteritems()], reverse=True)
    similar_ids = [id for p, id in sorted_tasks[:6]]
    similar = Task.objects.for_user(request.user, VIEW) \
            .filter(id__in=similar_ids).select_related('content')

    order_by_field = django_sorting.middleware.get_field(request)
    if len(order_by_field) > 1:
        similar = similar.order_by(order_by_field)

    similar = list(similar)

    return {
        'all_tasks': [task] + similar,
        'no_autosort': True,
        'task': task,
        'similar': similar,
        'view_type': 'similar_task_view_type',
    }

# final filename is 'attachments/task_id/attachment index/filename.ext'
ZIP_ATTACHMENT_DIR = 'attachments'

class _ConvertException(Exception):
    def __init__(self, invalid_tasks, *args, **kwargs):
        super(_ConvertException, self).__init__(*args, **kwargs)
        self.invalid_tasks = invalid_tasks



def _convert_to_latex(sorted_tasks, ignore_exceptions, **kwargs):
    """
    Attachments go to attachments/task_id/attachment_index/filename.ext.
    """
    is_latex = kwargs['format'] == 'latex'

    tasks = []
    invalid_tasks = []
    for k, x in enumerate(sorted_tasks):
        # no / at the end
        attachments_path = is_latex and '{}/{}'.format(ZIP_ATTACHMENT_DIR, x.id)
        try:
            content = convert_to_latex(x.content.text,
                    content=x.content, attachments_path=attachments_path)
        except:
            if not ignore_exceptions:
                invalid_tasks.append(x)
                continue
            escaped = latex_escape(x.content.text)
            content = "CONVERSION ERROR! Original text:\n" \
                    "\\begin{verbatim}\n%s\n\\end{verbatim}\n" % escaped
        data = {
            'title': x.name,
            'url': x.get_absolute_url(),
            'source': x.source,
            'index': k + 1,
            'id': x.id,
            'content': content,
        }

        tasks.append(data)

    if invalid_tasks:
        raise _ConvertException(invalid_tasks)

    return render_to_string(
        'latex_task_export.tex',
        dict(tasks=tasks, **kwargs)
    )

def _export(ids, sorted_tasks, tasks, form, ignore_exceptions):
    """
        Output LaTeX or PDF, permission already checked.
        It is assumed that Attachments are already saved in tasks[...] as
        .cache_file_list
    """
    format = form.cleaned_data['format']

    if format not in ['latex', 'pdf']:
        return (400, 'Export format not valid')

    # Please note that .tex created for .pdf is not the same as .tex for
    # exporting (e.g. there are differences in the attachment path).
    # Those two cases will be distinguished by different hashes.
    hash = hashlib.md5(repr((ids, form.cleaned_data))).hexdigest()

    create_archive = form.cleaned_data['create_archive']
    filename = os.path.normpath(os.path.join(settings.LOCAL_DIR,
        'media/export/task' + hash))    # no extension

    # check if output already exists
    ext = '.pdf' if format == 'pdf' else '.tex'
    fext = '.zip' if create_archive else ext         # final ext

    # TODO: check if archive exists (currently, it is not trivially possible
    # to check if there were some changes to attachments)
    if not settings.DEBUG \
            and not create_archive \
            and os.path.exists(filename + fext):
        oldest_file_mtime = \
                tasks.aggregate(Min('last_edit_date'))['last_edit_date__min']
        full_path = os.path.getmtime(filename + fext)
        if datetime.datetime.fromtimestamp(full_path) > oldest_file_mtime:
            # already up-to-date
            return HttpResponseRedirect(
                    '/media/export/task{}{}'.format(hash, fext))

    latex = _convert_to_latex(sorted_tasks, ignore_exceptions,
            **form.cleaned_data)

    # if latex without archive, do not create file, but directly output it
    if format == 'latex' and not create_archive:
        response = HttpResponse(content=latex, content_type='application/x-latex')
        response['Content-Disposition'] = 'filename=taskexport.tex'
        return response

    # otherwise, save generated latex into a file
    f = codecs.open(filename + '.tex', 'w', encoding='utf-8')
    f.write(latex)
    f.close()

    if format == 'pdf':
        error = run_command('pdflatex -output-directory=%s -interaction=batchmode %s.tex' \
            % (os.path.dirname(filename), filename), timeout=10)
        if error:
            return HttpResponseServerError('LaTeX generation error! Error code: %d' % error)

        # error = run_command('dvipdfm -o %s %s' % (filename + '.pdf', filename), timeout=10)
        # if error:
            # return HttpResponseServerError('dvipdfm Error %d!' % error)
        # os.remove(filename + '.tex')
        # os.remove(filename + '.log')
        # os.remove(filename + '.aux')
        # os.remove(filename + '.dvi')

    if create_archive:
        f = zipfile.ZipFile(filename + '.zip', mode='w',
            compression=zipfile.ZIP_DEFLATED)

        f.write(filename + ext, 'task{}{}'.format(hash, ext))
        for task in tasks:
            for k in range(len(task.cache_file_list)):
                attachment = task.cache_file_list[k]
                f.write(attachment.file.name, '{}/{}/{}/{}'.format(
                    ZIP_ATTACHMENT_DIR, task.id, k, attachment.get_filename()))

        f.close()

    return HttpResponseRedirect('/media/export/task{}{}'.format(hash, fext))


@response('task_export.html')
def export(request, format=None, ids=None):
    """
        Exports tasks with given ids to given format.
        Format and ids can be given as GET or POST information.
    """

    # Please note that both TaskExportForm and unnamed form (format, ids)
    # use POST method. To prevent collision, submit button in TaskExportForm
    # is named 'action'.

    POST = request.POST.copy()

    # Move URL / GET data to POST
    if format and ids:
        POST['format'] = format
        POST['ids'] = ids
    else:
        format = POST.get('format')
        ids  = POST.get('ids')


    available_formats = dict(EXPORT_FORMAT_CHOICES)
    if not ids or format not in available_formats:
        raise Http404

    try:
        id_list = [int(x) for x in ids.split(',')]
    except ValueError:
        raise Http404

    # check for permissions
    # TODO: use some permissions util method
    tasks = Task.objects.for_user(request.user, VIEW).filter(id__in=id_list).distinct()
    if len(tasks) != len(id_list):
        raise Http404('Neki od navedenih zadataka ne postoje ili su skriveni.')

    check_prerequisites_for_tasks(tasks, request.user)
    removed_tasks = [x for x in tasks if not x.cache_prerequisites_met]

    if removed_tasks:
        # Remove them for the list.
        id_list = [x.id for x in tasks if x.cache_prerequisites_met]
        ids = ','.join(str(x) for x in id_list)

    # permission ok, use shortened query
    tasks = Task.objects.filter(id__in=id_list)

    # keep the same order as in id_list
    task_position = {id: position for position, id in enumerate(id_list)}
    sorted_tasks = list(tasks)
    sorted_tasks.sort(key=lambda task: task_position[task.id])

    for x in sorted_tasks:
        x.cache_prerequisites_met = True

    # force queryset evaluation and prepare all attachments...
    content_to_task = {}
    for task in tasks:
        task.cache_file_list = []
        content_to_task[task.content_id] = task

    # attachments
    query = "SELECT A.* FROM mathcontent_attachment A"                  \
            " INNER JOIN task_task B ON A.content_id = B.content_id"    \
            " WHERE B.id IN ({})".format(ids)
    attachments = list(Attachment.objects.raw(query))
    for attachment in attachments:
        content_to_task[attachment.content_id].cache_file_list.append(attachment)

    invalid_tasks = None
    if request.method == 'POST' and 'action' in POST:
        form = TaskExportForm(POST)
        if form.is_valid():
            # note that attachments are imported into each task as .cache_file_list
            ignore_exceptions = request.POST.get('ignore-exceptions')
            try:
                return _export(ids, sorted_tasks, tasks, form,
                        ignore_exceptions)
            except _ConvertException as e:
                invalid_tasks = e.invalid_tasks

    # otherwise, if form not given or not valid:

    create_archive = len(attachments) > 0
    if len(id_list) == 1:
        data = (format, ids, True, True, True, False, False, create_archive)
    else:
        data = (format, ids, False, False, False, False, True, create_archive)

    data = dict(zip(('format', 'ids', 'has_title', 'has_url', 'has_source',
        'has_index', 'has_id', 'create_archive'), data))
    form = TaskExportForm(data)

    if len(attachments):
        form.fields['create_archive'].label = \
            'Zip arhiva (ukupno datoteka: {}+1)'.format(len(attachments))
    else:
        form.fields['create_archive'].widget = forms.HiddenInput()

    return {
        'all_tasks': removed_tasks + sorted_tasks,
        'attachments': attachments,
        'form': form,
        'format': available_formats[format],
        'invalid_tasks': invalid_tasks,
        'removed_tasks': removed_tasks,
        'tasks': sorted_tasks,
    }
