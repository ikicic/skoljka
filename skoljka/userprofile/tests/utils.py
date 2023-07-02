from django.contrib.auth.models import User

from skoljka.folder.models import Folder
from skoljka.utils.testcase import TestCase


class TestCaseWithUsers(TestCase):
    fixtures = ['skoljka/userprofile/fixtures/test_userprofiles.json']

    def setUp(self):
        super(TestCaseWithUsers, self).setUp()
        self.admin = User.objects.get(id=1)
        self.user1 = User.objects.get(id=2)
        self.user2 = User.objects.get(id=3)


class TestCaseWithUsersAndFolders(TestCaseWithUsers):
    fixtures = [
        'skoljka/userprofile/fixtures/test_userprofiles.json',
        'skoljka/folder/fixtures/test_folders.json',
    ]

    def load_folders(self):
        """Load folders from the fixtures. Not loading by default to avoid
        slowing down the tests."""
        # Trying to store the folder hierarchy in the name...
        self.folder0 = Folder.objects.get(id=1)
        self.folder00 = Folder.objects.get(id=2)
        self.folder000 = Folder.objects.get(id=3)
        self.folder0000 = Folder.objects.get(id=4)
