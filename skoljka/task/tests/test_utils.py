from django.contrib.auth.models import User
from django.test import TestCase

from skoljka.mathcontent.models import MathContent
from skoljka.permissions.constants import EDIT, EDIT_PERMISSIONS, VIEW
from skoljka.task.models import Task


class TaskUtilsTestCase(TestCase):
    fixtures = ['skoljka/userprofile/fixtures/test_userprofiles.json']

    def setUp(self):
        content1 = MathContent.objects.create(text="Test text for the task")
        self.user1 = User.objects.get(id=1)
        self.user2 = User.objects.get(id=2)
        self.task1 = Task.objects.create(
            name="First example task", author=self.user1, content=content1
        )

    def test_author_permissions(self):
        self.assertEqual(
            set(self.task1.get_user_permissions(self.user1)),
            set([VIEW, EDIT, EDIT_PERMISSIONS]),
        )
