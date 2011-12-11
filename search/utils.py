from task.models import Task

from taggit.utils import parse_tags


def split_tags(tags):
    if type(tags) is unicode:
        tags = parse_tags(tags)
    if type(tags) is not list:
        tags = []
    return filter(None, [x.strip() for x in tags])

def search_tasks(tags=[], none_if_blank=True):
    tags = split_tags(tags)
    if none_if_blank and not tags:
        return Task.objects.none()

    tasks = Task.objects.all()
    for tag in tags:
        tasks = tasks.filter(tags__name__iexact=tag)
    
    return tasks
