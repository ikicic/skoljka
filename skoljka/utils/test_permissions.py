from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from skoljka.apps.problems.models import Problem
from skoljka.tests.factories import (
    make_list,
    make_problem,
    make_source,
    make_staff,
    make_user,
)


class PermissionQuerySetForUserTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = make_user(username="alice")
        cls.bob = make_user(username="bob")
        cls.staff = make_staff(username="root")
        cls.anon = AnonymousUser()

        cls.public_by_alice = make_problem(created_by=cls.alice)
        cls.private_by_alice = make_problem(
            created_by=cls.alice, is_public=False
        )
        cls.private_by_bob = make_problem(
            created_by=cls.bob, is_public=False
        )

    def _ids(self, qs):
        return set(qs.values_list("id", flat=True))

    def test_anonymous_sees_only_public(self):
        ids = self._ids(Problem.objects.for_user(self.anon))
        self.assertEqual(ids, {self.public_by_alice.id})

    def test_authenticated_sees_public_plus_own(self):
        ids = self._ids(Problem.objects.for_user(self.alice))
        self.assertEqual(ids, {self.public_by_alice.id, self.private_by_alice.id})

    def test_staff_sees_all(self):
        ids = self._ids(Problem.objects.for_user(self.staff))
        self.assertEqual(
            ids,
            {self.public_by_alice.id, self.private_by_alice.id, self.private_by_bob.id},
        )

    def test_edit_permission_returns_only_own(self):
        ids = self._ids(Problem.objects.for_user(self.alice, "edit"))
        self.assertEqual(ids, {self.public_by_alice.id, self.private_by_alice.id})

    def test_edit_permission_excludes_others_public(self):
        ids = self._ids(Problem.objects.for_user(self.bob, "edit"))
        self.assertEqual(ids, {self.private_by_bob.id})


class UserHasPermTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user(username="owner")
        cls.other = make_user(username="other")
        cls.staff = make_staff(username="staff")
        cls.anon = AnonymousUser()
        cls.public = make_problem(created_by=cls.owner, is_public=True)
        cls.private = make_problem(created_by=cls.owner, is_public=False)

    def test_staff_always_true(self):
        self.assertTrue(self.private.user_has_perm(self.staff, "view"))
        self.assertTrue(self.private.user_has_perm(self.staff, "edit"))

    def test_view_on_public_true_for_anon(self):
        self.assertTrue(self.public.user_has_perm(self.anon, "view"))

    def test_view_on_private_false_for_non_owner(self):
        self.assertFalse(self.private.user_has_perm(self.other, "view"))

    def test_view_on_private_true_for_owner(self):
        self.assertTrue(self.private.user_has_perm(self.owner, "view"))

    def test_edit_on_public_false_for_non_owner(self):
        self.assertFalse(self.public.user_has_perm(self.other, "edit"))


class PermissionViewLeakTest(TestCase):
    """Private Problem / Source / ProblemList detail must not leak to unauth users."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user(username="owner")
        cls.private_problem = make_problem(
            created_by=cls.owner, is_public=False, content="Hidden"
        )
        cls.private_source = make_source(
            slug="secret-s", name="Secret", created_by=cls.owner, is_public=False
        )
        cls.private_list = make_list(
            title="Secret list", created_by=cls.owner, is_public=False
        )

    def test_problem_detail_hidden_from_anon(self):
        r = self.client.get(f"/problems/{self.private_problem.id}/")
        self.assertEqual(r.status_code, 404)

    def test_source_detail_hidden_from_anon(self):
        r = self.client.get(f"/archive/{self.private_source.slug}/")
        self.assertEqual(r.status_code, 404)

    def test_list_detail_hidden_from_anon(self):
        r = self.client.get(f"/lists/{self.private_list.pk}/")
        self.assertEqual(r.status_code, 404)
