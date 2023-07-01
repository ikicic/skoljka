from skoljka.mathcontent.models import MathContent
from skoljka.task.models import Task


def create_task(author, title, text, **kwargs):
    """Create a dummy task."""
    mc = MathContent(text=text)
    mc.save()
    task = Task(author=author, name=title, content=mc, **kwargs)
    task.save()
    return task
