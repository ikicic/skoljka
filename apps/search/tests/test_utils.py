from django.contrib.auth.models import User
from django.test import TestCase

from mathcontent.models import MathContent
from tags.utils import add_tags, remove_tags, set_tags
from task.models import Task
from search.utils import search_tasks

def _create_task(author, tags, hidden):
    content = MathContent.objects.create(text="Test text", html="Test text")
    task = Task.objects.create(name="Test task", content=content,
            author=author, hidden=hidden)
    set_tags(task, tags)
    return task

class SearchTest(TestCase):
    fixtures = ['apps/userprofile/fixtures/test_userprofiles.json']

    def setUp(self):
        # TODO: make a base class for users
        self.admin = User.objects.get(id=1)
        self.alice = User.objects.get(id=2)

        self.task1 = _create_task(self.admin, "foo", False)
        self.task2 = _create_task(self.admin, "bar", False)
        self.task3 = _create_task(self.admin, "foo,bar", False)
        self.task4 = _create_task(self.admin, "bla", False)
        self.task5 = _create_task(self.admin, "bar, bla", False)

    def assertSearchTask(self, query, results):
        self.assertEqual(set(search_tasks(query)), set(results))

    # TODO: test search()
    # TODO: test special features of search_tasks()

    def test_search_tasks(self):
        self.assertSearchTask("foo", [self.task1, self.task3])
        self.assertSearchTask("bar", [self.task2, self.task3, self.task5])
        self.assertSearchTask("foo, bar", [self.task3])
        self.assertSearchTask("foo, bar, bla", [])

    def test_update_search_cache_add_tag(self):
        self.assertSearchTask("foo", [self.task1, self.task3])
        add_tags(self.task2, "foo")
        self.assertSearchTask("foo", [self.task1, self.task2, self.task3])
        add_tags(self.task2, "foo")
        self.assertSearchTask("foo", [self.task1, self.task2, self.task3])

    def test_update_search_cache_remove_tag(self):
        self.assertSearchTask("foo", [self.task1, self.task3])
        remove_tags(self.task1, "foo")
        self.assertSearchTask("foo", [self.task3])
        remove_tags(self.task3, "foo")
        self.assertSearchTask("foo", [])
