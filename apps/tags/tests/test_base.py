from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from mathcontent.models import MathContent
from task.models import Task

from tags.models import Tag, TaggedItem

def get_tags(instance):
    # no cache!
    content_type = ContentType.objects.get_for_model(instance)
    return TaggedItem.objects \
            .filter(content_type=content_type, object_id=instance.id) \
            .values_list('tag__name', flat=True)


class TagsTestCaseBase(TestCase):
    fixtures = ['apps/userprofile/fixtures/test_userprofiles.json']

    def setUp(self):
        tags = ["IMO", "MEMO", "alg", "geo", "komb", "tb"]
        # Do not use bulk_create, it doesn't call .save()
        for tag in tags:
            Tag.objects.create(name=tag)

    def _set_up_tasks(self):
        self.user1 = User.objects.get(id=1)
        self.user2 = User.objects.get(id=2)
        content1 = MathContent.objects.create(text="Test text for the task1")
        content2 = MathContent.objects.create(text="Test text for the task2")
        self.task1 = Task.objects.create(name="First", content=content1,
                author=self.user1)
        self.task2 = Task.objects.create(name="Second", content=content2,
                author=self.user2)
        self.task1.tags.set("MEMO", "alg")
        self.task2.tags.set("IMO", "geo")

    def assertTagsEqual(self, tags, expected):
        self.assertItemsEqual(get_tags(tags), expected)


