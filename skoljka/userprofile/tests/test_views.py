from __future__ import print_function

import re

from django.contrib import auth
from django.contrib.auth.models import Group, User
from django.core import mail

import skoljka.userprofile.forms as userprofile_forms
from skoljka.mathcontent.latex import LatexElement
from skoljka.userprofile.challenge import Challenge, TestChallengeHandler
from skoljka.userprofile.forms import CHALLENGE_ANSWER, CHALLENGE_KEY
from skoljka.userprofile.models import UserProfile
from skoljka.utils.testcase import TestCase

TEST_CHALLENGE_KEY_VALUE = 'TESTKEY-ANSWER-50'
TEST_CHALLENGE_ANSWER_VALUE = '50'


class MockChallengeHandler(TestChallengeHandler):
    @staticmethod
    def get_or_generate_png(format, content):
        return LatexElement(hash='abcdef', format=format, text=content, depth=5)

    def from_key(self, key):
        if key == TEST_CHALLENGE_KEY_VALUE:
            return Challenge(index=3)  # 30 + sqrt(400)
        else:
            return super(MockChallengeHandler, self).from_key(key)


class UserViewsTestCase(TestCase):
    def setUp(self):
        self._old_challenge_handler = userprofile_forms.challenge_handler
        userprofile_forms.challenge_handler = MockChallengeHandler()

    def tearDown(self):
        userprofile_forms.challenge_handler = self._old_challenge_handler

    def test_registration_and_login(self):
        def has_form_error(response):
            return 'error' in response.content

        # Check everything is clean at the start.
        self.assertEqual(User.objects.all().count(), 0)
        self.assertEqual(Group.objects.all().count(), 0)
        self.assertEqual(UserProfile.objects.all().count(), 0)
        self.assertEqual(len(mail.outbox), 0)

        c = self.client

        # Test the page without POST arguments.
        response = c.get('/accounts/register/')
        self.assertEqual(response.status_code, 200)

        # Test reject if TOU not accepted.
        response = c.post(
            '/accounts/register/',
            {
                'username': 'testaccount',
                'email': 'dummy@example.com',
                'password1': 'testpwd',
                'password2': 'testpwd',
                CHALLENGE_KEY: TEST_CHALLENGE_KEY_VALUE,
                CHALLENGE_ANSWER: TEST_CHALLENGE_ANSWER_VALUE,
            },
        )
        self.assertEqual(User.objects.all().count(), 0)
        self.assertTrue(has_form_error(response))

        # Test invalid email.
        response = c.post(
            '/accounts/register/',
            {
                'username': 'testaccount',
                'email': 'this-is-not-an-email',
                'password1': 'testpwd',
                'password2': 'testpwd',
                CHALLENGE_KEY: TEST_CHALLENGE_KEY_VALUE,
                CHALLENGE_ANSWER: TEST_CHALLENGE_ANSWER_VALUE,
                'tou': 'on',
            },
        )
        self.assertEqual(User.objects.all().count(), 0)
        self.assertTrue(has_form_error(response))

        # Test mismatched passwords.
        response = c.post(
            '/accounts/register/',
            {
                'username': 'testaccount',
                'email': 'test@example.com',
                'password1': 'testpwd',
                'password2': 'testpwdwrong',
                CHALLENGE_KEY: TEST_CHALLENGE_KEY_VALUE,
                CHALLENGE_ANSWER: TEST_CHALLENGE_ANSWER_VALUE,
                'tou': 'on',
            },
        )
        self.assertEqual(User.objects.all().count(), 0)
        self.assertTrue(has_form_error(response))

        # Test valid registration.  <--------------
        response = c.post(
            '/accounts/register/',
            {
                'username': 'testaccount',
                'email': 'test@example.com',
                'password1': 'testpwd',
                'password2': 'testpwd',
                CHALLENGE_KEY: TEST_CHALLENGE_KEY_VALUE,
                CHALLENGE_ANSWER: TEST_CHALLENGE_ANSWER_VALUE,
                'tou': 'on',
            },
        )
        self.assertEqual(User.objects.all().count(), 1)
        self.assertFalse(has_form_error(response))
        self.assertEqual(len(mail.outbox), 1)

        # Test used username.
        response = c.post(
            '/accounts/register/',
            {
                'username': 'testaccount',
                'email': 'anothertest@example.com',
                'password1': 'testpwd',
                'password2': 'testpwd',
                CHALLENGE_KEY: TEST_CHALLENGE_KEY_VALUE,
                CHALLENGE_ANSWER: TEST_CHALLENGE_ANSWER_VALUE,
                'tou': 'on',
            },
        )
        self.assertEqual(User.objects.all().count(), 1)
        self.assertTrue(has_form_error(response))
        self.assertEqual(len(mail.outbox), 1)

        # Test used email.
        response = c.post(
            '/accounts/register/',
            {
                'username': 'anothertestaccount',
                'email': 'test@example.com',
                'password1': 'testpwd',
                'password2': 'testpwd',
                CHALLENGE_KEY: TEST_CHALLENGE_KEY_VALUE,
                CHALLENGE_ANSWER: TEST_CHALLENGE_ANSWER_VALUE,
                'tou': 'on',
            },
        )
        self.assertEqual(User.objects.all().count(), 1)
        self.assertTrue(has_form_error(response))
        self.assertEqual(len(mail.outbox), 1)

        # Continue testing the registered user.
        user = User.objects.get(username='testaccount')
        self.assertEqual(UserProfile.objects.all().count(), 1)
        profile = user.get_profile()  # Test that profile was created.
        self.assertIsNotNone(profile)
        self.assertEqual(Group.objects.all().count(), 1)
        group = Group.objects.get(name='testaccount')
        self.assertEqual(
            list(group.user_set.all()),
            [user],
            "User's private group should point to the user.",
        )

        # Test that the user is not active before confirming the email.
        self.assertFalse(user.is_active, "The user should not be active yet.")
        self.assertEqual(user.email, 'test@example.com')
        response = c.post(
            '/accounts/login/',
            {  # Inactive users cannot login.
                'username': 'testaccount',
                'password': 'testpwd',
            },
        )
        # FIXME: Invalid username or password message is missing!
        self.assertFalse(auth.get_user(c).is_authenticated())

        # Test confirmation email and confirming the email address.
        match = re.search(r'(/accounts/activate/.*)', mail.outbox[0].body)
        self.assertIsNotNone(match)
        # FIXME: Add a trailing slash in the email.
        response = c.get(match.group(0) + '/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertTrue(
            response.redirect_chain[0][0].endswith('/accounts/activate/complete/')
        )

        user = User.objects.get(username='testaccount')
        self.assertTrue(user.is_active)
        self.assertEqual(
            auth.get_user(c),
            user,
            "User is automatically logged in after confirmation.",
        )

        # Test logout.
        response = c.get('/accounts/logout/', follow=True)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertRegex(
            response.redirect_chain[0][0],
            r'https?://[a-z.]+/',
            "Should go to home page.",
        )

        # Test login after confirming the email.
        self.assertIsNone(auth.get_user(c).id)
        response = c.post(
            '/accounts/login/',
            {
                'username': 'testaccount',
                'password': 'testpwd',
            },
        )
        self.assertEqual(auth.get_user(c), user)
