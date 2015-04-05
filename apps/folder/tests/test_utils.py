from django.test import TestCase

from folder.models import Folder
from folder.utils import get_folder_descendant_ids

class TaskUtilsTestCase(TestCase):
    fixtures = ['apps/folder/fixtures/test_folders.json']

    def setUp(self):
        pass

    def test_get_folder_descendant_ids(self):
        self.assertEqual(sorted(get_folder_descendant_ids(1)), [2, 3, 4])
        self.assertEqual(sorted(get_folder_descendant_ids(2)), [3, 4])
        self.assertEqual(sorted(get_folder_descendant_ids(3)), [])
        self.assertEqual(sorted(get_folder_descendant_ids(4)), [])
