from task.models import Task

def splitTags(tags):
    if type(tags) is unicode:
        tags = tags.split(',')
    if type(tags) is not list:
        tags = []
    return filter(None, [x.strip() for x in tags])


def searchTasks(tags=[], noneIfBlank=True):
    tags = splitTags(tags)
    if noneIfBlank and not tags:
        return None

    tasks = Task.objects.all()
    for tag in tags:
        tasks = tasks.filter(tags__name__iexact=tag)
    
    return tasks
