from django.test import TestCase

from skoljka.folder.models import Folder
from skoljka.folder.utils import get_folder_descendant_ids

# TODO: Do not use fixtures.
# TODO: Tests.

class TaskUtilsTestCase(TestCase):
    fixtures = ['skoljka/folder/fixtures/test_folders.json']

    def setUp(self):
        pass

    def test_get_folder_descendant_ids(self):
        self.assertEqual(sorted(get_folder_descendant_ids(1)), [2, 3, 4])
        self.assertEqual(sorted(get_folder_descendant_ids(2)), [3, 4])
        self.assertEqual(sorted(get_folder_descendant_ids(3)), [])
        self.assertEqual(sorted(get_folder_descendant_ids(4)), [])
