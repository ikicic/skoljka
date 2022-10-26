import json

from django import forms

from skoljka.utils.decorators import ajax, response

from skoljka.task.bulk_format import BulkFormatError, parse_bulk
from skoljka.task.forms import check_prerequisites

@ajax(post=['text'])
@response('inc_task_bulk_preview_multiple.html')
def bulk_preview(request):
    """This basically simulates task_bulk_preview_multiple tag."""
    try:
        task_infos = parse_bulk(request.user, request.POST['text'])
    except BulkFormatError as e:
        return e.message

    return {'task_infos': task_infos}


@ajax(get=['ids'])
def prerequisites(request):
    task_id = request.GET.get('task_id')
    if task_id:
        task_id = int(task_id)
    try:
        ids, accessible = check_prerequisites(request.GET['ids'],
            request.user, task_id)
    except forms.ValidationError as e:
        return json.dumps(e.messages[0])

    return json.dumps({x.id: x.name for x in accessible})
