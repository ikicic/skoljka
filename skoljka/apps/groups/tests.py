from django.db import IntegrityError
from django.test import TestCase

from skoljka.apps.groups.models import Group, GroupMembership
from skoljka.tests.factories import make_user


class PersonalGroupSignalTest(TestCase):
    def test_creating_user_creates_personal_group(self):
        u = make_user(username="signal1")
        self.assertIsNotNone(u.personal_group)
        self.assertTrue(u.personal_group.personal)

    def test_personal_group_membership_is_admin(self):
        u = make_user(username="signal2")
        membership = GroupMembership.objects.get(group=u.personal_group, user=u)
        self.assertEqual(membership.role, GroupMembership.Role.ADMIN)

    def test_one_personal_group_per_user(self):
        u = make_user(username="signal3")
        initial = Group.objects.filter(pk=u.personal_group.pk).count()
        self.assertEqual(initial, 1)
        u.ensure_personal_group()
        self.assertEqual(Group.objects.filter(pk=u.personal_group.pk).count(), 1)

    def test_ensure_personal_group_idempotent(self):
        u = make_user(username="signal4")
        pg_id = u.personal_group_id
        u.ensure_personal_group()
        u.refresh_from_db()
        self.assertEqual(u.personal_group_id, pg_id)


class GroupMembershipUniqueTest(TestCase):
    def test_unique_group_user_pair(self):
        u = make_user(username="gmu")
        group = u.personal_group
        with self.assertRaises(IntegrityError):
            GroupMembership.objects.create(
                group=group, user=u, role=GroupMembership.Role.EDITOR
            )
