from django import forms

from skoljka.utils.decorators import ajax

from task.forms import check_prerequisites

import json

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
