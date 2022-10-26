from django.contrib.auth.models import User
from django.test import TestCase

from skoljka.mathcontent.models import MathContent
from skoljka.permissions.constants import \
        VIEW, EDIT, EDIT_PERMISSIONS, VIEW_SOLUTIONS
from skoljka.permissions.models import ObjectPermission
from skoljka.solution.models import Solution, SolutionStatus, SOLUTION_CORRECT_SCORE

from skoljka.task.models import Task
from skoljka.task.utils import check_prerequisites_for_task, \
        check_prerequisites_for_tasks

# Shorthands
CHECK_ONE = check_prerequisites_for_task
CHECK_MULTIPLE = check_prerequisites_for_tasks

class TaskUtilsTestCase(TestCase):
    fixtures = ['skoljka/userprofile/fixtures/test_userprofiles.json']

    def setUp(self):
        content1 = MathContent.objects.create(text="Test text for the task")
        content2 = MathContent.objects.create(text="Test text for the task")
        self.user1 = User.objects.get(id=1)
        self.user2 = User.objects.get(id=2)
        self.task1 = Task.objects.create(
                name="First example task",
                author=self.user1,
                content=content1)
        self.task2 = Task.objects.create(
                name="Second example task",
                author=self.user2,
                content=content2,
                prerequisites=str(self.task1.id)) # With prerequisites

    def test_author_permissions(self):
        self.assertEqual(set(self.task1.get_user_permissions(self.user1)),
                set([VIEW, EDIT, EDIT_PERMISSIONS, VIEW_SOLUTIONS]))

    def _check_prereqs(self, tasks, user, expected):
        """
        Checks prerequisites for given tasks for "current" user.
        """
        check_prerequisites_for_tasks(tasks, user)
        for k, task in enumerate(tasks):
            msg = "{} is not {} for k = {}".format(
                    not expected[k], expected[k], k)
            self.assertEqual(task.cache_prerequisites_met, expected[k], msg=msg)

    def test_prerequisites(self):
        self.assertTrue(CHECK_ONE(self.task1, self.user1))
        self.assertTrue(CHECK_ONE(self.task1, self.user2))
        self.assertFalse(CHECK_ONE(self.task2, self.user1))
        self.assertTrue(CHECK_ONE(self.task2, self.user2))

    def test_prerequisites_1(self):
        self._check_prereqs([self.task1, self.task2], self.user1, [True, False])

    def test_prerequisites_2(self):
        self._check_prereqs([self.task1, self.task2], self.user2, [True, True])

    def test_prerequisites_submitted(self):
        content = MathContent.objects.create(text="Test text for the solution")
        solution = Solution.objects.create(task=self.task1, author=self.user1,
            content=content, status=SolutionStatus.SUBMITTED,
            correctness_avg=SOLUTION_CORRECT_SCORE) # Solved
        self.assertTrue(CHECK_ONE(self.task2, self.user1))

        solution.correctness_avg = SOLUTION_CORRECT_SCORE / 2. # Not solved
        solution.save()
        self.assertFalse(CHECK_ONE(self.task2, self.user1))

    def test_view_solutions_permission(self):
        # If user didn't met the prerequisites:
        # Without explicit permissions, user can't access the task.
        self.assertFalse(CHECK_ONE(self.task2, self.user1))

        # With explicit permission, he/she can access the task.
        self.assertTrue(CHECK_ONE(self.task2, self.user1, perm=[VIEW_SOLUTIONS]))

        # With explicit permission, he/she can access the task.
        ObjectPermission.objects.create(permission_type=VIEW_SOLUTIONS,
            content_object=self.task2,
            group=self.user1.get_profile().private_group)
        self.assertTrue(CHECK_ONE(self.task2, self.user1))
