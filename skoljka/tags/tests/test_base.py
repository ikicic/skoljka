from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from skoljka.mathcontent.models import MathContent
from skoljka.tags.models import Tag, TaggedItem
from skoljka.tags.utils import set_tags
from skoljka.task.models import Task


def get_tags(instance):
    # no cache!
    content_type = ContentType.objects.get_for_model(instance)
    return TaggedItem.objects.filter(
        content_type=content_type, object_id=instance.id
    ).values_list('tag__name', flat=True)


class TagsTestCaseBase(TestCase):
    fixtures = ['skoljka/userprofile/fixtures/test_userprofiles.json']

    def setUp(self):
        tags = ["IMO", "MEMO", "alg", "geo", "komb", "tb"]
        # Do not use bulk_create, it doesn't call .save()
        for tag in tags:
            Tag.objects.create(name=tag)

    def _set_up_tasks(self):
        # TODO: add base test for model with userprofiles.
        self.admin = User.objects.get(id=1)
        self.alice = User.objects.get(id=2)
        content1 = MathContent.objects.create(text="Test text for the task1")
        content2 = MathContent.objects.create(text="Test text for the task2")
        self.admin_task = Task.objects.create(
            name="First", content=content1, author=self.admin, hidden=True
        )
        self.alice_task = Task.objects.create(
            name="Second", content=content2, author=self.alice, hidden=True
        )
        set_tags(self.admin_task, ["IMO", "geo"])
        set_tags(self.alice_task, ["MEMO", "alg"])

    def assertTagsEqual(self, tags, expected):
        self.assertItemsEqual(get_tags(tags), expected)
