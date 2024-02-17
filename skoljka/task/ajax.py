from skoljka.task.bulk_format import BulkFormatError, parse_bulk
from skoljka.utils.decorators import ajax, response


@ajax(post=['text'])
@response('inc_task_bulk_preview_multiple.html')
def bulk_preview(request):
    """This basically simulates task_bulk_preview_multiple tag."""
    try:
        task_infos = parse_bulk(request.user, request.POST['text'])
    except BulkFormatError as e:
        return e.message

    return {'task_infos': task_infos}
