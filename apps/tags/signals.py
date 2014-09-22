from django.dispatch import Signal

from task.models import Task

task_tags_changed_high_priority = Signal(providing_args=['old_tags', 'new_tags'])
task_tags_changed = Signal(providing_args=['old_tags', 'new_tags'])

def send_task_tags_changed_signal(task, old_tags, new_tags):
    if set(old_tags) != set(new_tags):
        task_tags_changed_high_priority.send(sender=Task, instance=task,
                old_tags=old_tags, new_tags=new_tags)
        task_tags_changed.send(sender=Task, instance=task,
                old_tags=old_tags, new_tags=new_tags)
