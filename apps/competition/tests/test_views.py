from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import Client

from permissions.constants import VIEW
from permissions.models import ObjectPermission

from competition.models import Competition, CompetitionTask, Chain, \
        Submission, Team, TeamMember
from competition.tests.test_utils import create_ctask

import datetime

DAY = datetime.timedelta(days=1)
HOUR = datetime.timedelta(hours=1)
class CompetitionViewsTestBase(TestCase):
    fixtures = ['apps/userprofile/fixtures/test_userprofiles.json']

    def setUp(self):
        """
        Competition description:

        #1 = registration not open yet
        #2 = registration open, competition not started
        #3 = competition started, not finished
        #4 = competition finished
        #5 = hidden, competition started, not finished
        """

        # TODO: make a base class for users
        self.admin = User.objects.get(id=1)
        self.alice = User.objects.get(id=2)
        self.bob = User.objects.get(id=3)
        self.client = Client()

        now = datetime.datetime.now()
        past1 = now - DAY
        past2 = past1 - DAY
        past3 = past2 - DAY
        future1 = now + DAY
        future2 = future1 + DAY
        future3 = future2 + DAY

        # ID, hidden, registration_open_date, start_date, end_date.
        competitions = [
            (1, False, future1, future2, future3),
            (2, False, past1, future2, future3),
            (3, False, past2, past1, future3),
            (4, False, past3, past2, past1),
            (5, True, past2, past1, future3),
        ]
        competitions = [
            Competition(name="Test competition #{}".format(a), hidden=b,
                registration_open_date=c, start_date=d, end_date=e,
                scoreboard_freeze_date=e - HOUR)
            for a, b, c, d, e in competitions
        ]
        Competition.objects.bulk_create(competitions)
        self.competitions = {x.id: x for x in Competition.objects.all()}

    def login(self, user):
        self.assertTrue(self.client.login(username=user.username, password="a"))

    def logout(self):
        self.client.logout()


class RegistrationTest(CompetitionViewsTestBase):
    def test_hidden_not_logged_in(self):
        """If not logged in, it shouldn't work."""
        response = self.client.get('/competition/5/registration/')
        self.assertEqual(response.status_code, 403)

    def test_hidden_logged_in_no_permission(self):
        """If random user logged in, it shouldn't work."""
        self.login(self.alice)
        response = self.client.get('/competition/5/registration/')
        self.assertEqual(response.status_code, 403)
        self.logout()

    def test_hidden_admin_logged_in_no_permission(self):
        """If admin logged in, without a permission, it shouldn't work."""
        self.login(self.admin)
        response = self.client.get('/competition/5/registration/')
        self.assertEqual(response.status_code, 403)
        self.logout()

    def test_hidden_with_permission(self):
        """With explicit permission, it should work."""
        competition = Competition.objects.get(id=5)
        ObjectPermission.objects.create(content_object=competition,
                permission_type=VIEW,
                group=self.alice.get_profile().private_group)

        # It doesn't have to work even for admin_group if no explicit
        # permission is given. That's why we have permission system.

    def test_registration_unopened_redirect(self):
        """If registration unopened, redirect to competition homepage."""
        response = self.client.get('/competition/1/registration/')
        self.assertRedirects(response, '/competition/1/')

    def test_registration_unopened_admin_accept(self):
        """Even if registration unopened for public, it should be open for
        admins."""
        self.login(self.admin)
        response = self.client.get('/competition/1/registration/')
        self.assertEqual(response.status_code, 200)

    def test_registration_closed_redirect(self):
        """If registration closed, registration requests should be ignored and
        redirected to competition homepage."""
        self.login(self.alice)
        response = self.client.post('/competition/4/registration/',
                {'name': "Team name"})
        self.assertRedirects(response, '/competition/4/')
        self.logout()

    def test_registration_single_member(self):
        """Test registration without any additional members."""
        self.login(self.alice)
        response = self.client.post('/competition/2/registration/',
                {'name': "Team name"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'competition_registration_complete.html')
        self.assertIsNotNone(response.context['team'])
        self.assertEqual(response.context['team'].name, "Team name")
        self.assertEqual(TeamMember.objects.all().count(), 1)
        self.logout()

    def test_registration_one_invite_and_accept(self):
        """Test full registration with two members."""
        self.login(self.alice)
        response = self.client.post('/competition/2/registration/',
                {'name': "Team name", "member2_user_id": self.admin.id})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'competition_registration_complete.html')
        team = response.context['team']
        self.assertIsNotNone(team)
        self.assertEqual(team.name, "Team name")
        self.assertEqual(TeamMember.objects.filter(
            invitation_status=TeamMember.INVITATION_ACCEPTED).count(), 1)
        self.assertEqual(TeamMember.objects.filter(
            invitation_status=TeamMember.INVITATION_UNANSWERED).count(), 1)
        self.logout()

        self.login(self.admin)
        response = self.client.post('/competition/2/registration/',
                {'invitation-accept': team.id})
        self.assertIsNotNone(response.context['team'])
        self.assertEqual(TeamMember.objects.filter(
            invitation_status=TeamMember.INVITATION_ACCEPTED).count(), 2)
        self.assertEqual(TeamMember.objects.filter(
            invitation_status=TeamMember.INVITATION_UNANSWERED).count(), 0)
        self.logout()

    def test_same_user_in_two_competitions(self):
        """User should be able to join multiple competitions, also using the
        same team name."""
        self.login(self.alice)
        self.client.post('/competition/2/registration/', {'name': "same-name"})
        self.assertEqual(Team.objects.all().count(), 1)
        self.assertEqual(TeamMember.objects.all().count(), 1)
        response = self.client.post('/competition/3/registration/',
                {'name': "same-name"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Team.objects.all().count(), 2)
        self.assertEqual(TeamMember.objects.all().count(), 2)

    def test_delete_invitations_after_creating_a_team(self):
        self.login(self.alice)
        self.client.post('/competition/2/registration/',
                {'name': "Alice's team", "member2_user_id": self.bob.id})
        self.assertEqual(TeamMember.objects \
                .filter(team_id=1, member_id=self.bob.id).count(), 1)
        self.logout()
        self.login(self.bob)
        self.client.post('/competition/2/registration/', {'name': "Bob's team"})
        self.assertEqual(TeamMember.objects \
                .filter(team_id=1, member_id=self.bob.id).count(), 0)

    def test_delete_other_invitations_after_accepting_one(self):
        """Other invitations in the same competition should be deleted after
        selecting one. Invitations from other competition shouldn't be
        affected."""
        self.login(self.alice)
        self.client.post('/competition/2/registration/',
                {'name': "Alice 2", "member2_user_id": self.admin.id})
        self.client.post('/competition/3/registration/',
                {'name': "Alice 3", "member2_user_id": self.admin.id})
        self.logout()
        self.login(self.bob)
        response = self.client.post('/competition/2/registration/',
                {'name': "Bob 2", "member2_user_id": self.admin.id})
        self.assertEqual(response.status_code, 200)
        self.logout()
        self.login(self.admin)
        self.assertEqual(
                TeamMember.objects.filter(team__competition_id=2).count(), 4)
        self.assertEqual(
                TeamMember.objects.filter(team__competition_id=3).count(), 2)
        self.client.post('/competition/2/registration/',
                {'invitation-accept': 1})
        self.assertEqual(
                TeamMember.objects.filter(team__competition_id=2).count(), 3)
        self.assertEqual(
                TeamMember.objects.filter(team__competition_id=3).count(), 2)


class SubmissionTest(CompetitionViewsTestBase):
    def init_competition(self, competition, user):
        self.team = Team.objects.create(name="Test team", author=user,
                competition=competition)
        TeamMember.objects.create(team=self.team, member=user,
                member_name=user.username,
                invitation_status=TeamMember.INVITATION_ACCEPTED)
        self.chain = Chain.objects.create(competition=competition,
                name="Test chain", bonus_score=1000)
        self.ctask1 = create_ctask(self.admin, competition, self.chain, "42", 1)
        self.ctask2 = create_ctask(self.admin, competition, self.chain, "42", 10)
        self.ctask3 = create_ctask(self.admin, competition, self.chain, "42", 100)

    def _send_solution(self, task, result):
        return self.client.post(task.get_absolute_url(), {'result': result})

    def _delete_solution(self, task, submission_id):
        return self.client.post(task.get_absolute_url(),
                {'delete-submission': submission_id})

    def test_before_contest_start(self):
        self.init_competition(self.competitions[2], self.alice)
        self.login(self.alice)
        response = self._send_solution(self.ctask1, "-5")
        self.assertEqual(response.status_code, 404)
        self.logout()

    def test_after_contest_end(self):
        self.init_competition(self.competitions[4], self.alice)
        self.login(self.alice)
        response = self._send_solution(self.ctask1, "42")
        self.assertEqual(Submission.objects.all().count(), 0)
        self.assertEqual(self.team.cache_score, 0)
        self.logout()

    def test_incorrect(self):
        self.init_competition(self.competitions[3], self.alice)
        self.login(self.alice)
        response = self._send_solution(self.ctask1, "-5")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Submission.objects.all().count(), 1)
        self.assertEqual(self.team.cache_score, 0)
        self.logout()

    def test_correct(self):
        self.init_competition(self.competitions[3], self.alice)
        self.login(self.alice)
        response = self._send_solution(self.ctask1, "42")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Submission.objects.all().count(), 1)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 1)
        self.logout()

    def test_unlocked(self):
        self.init_competition(self.competitions[3], self.alice)
        self.login(self.alice)
        response = self._send_solution(self.ctask2, "42")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Submission.objects.all().count(), 0)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 0)
        self.logout()

    def test_correctly_finish_chain(self):
        self.init_competition(self.competitions[3], self.alice)
        self.login(self.alice)
        response = self._send_solution(self.ctask1, "42")
        self.assertEqual(Submission.objects.all().count(), 1)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 1)
        response = self._send_solution(self.ctask2, "42")
        self.assertEqual(Submission.objects.all().count(), 2)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 11)
        response = self._send_solution(self.ctask3, "42")
        self.assertEqual(Submission.objects.all().count(), 3)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 1111)
        self.logout()

    def test_unlock_if_try_limit_exceeded(self):
        self.init_competition(self.competitions[3], self.alice)
        self.login(self.alice)
        response = self._send_solution(self.ctask1, "-5")
        response = self._send_solution(self.ctask1, "-4")
        response = self._send_solution(self.ctask1, "-3")
        self.assertEqual(Submission.objects.all().count(), 3)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 0)
        response = self._send_solution(self.ctask2, "42")
        self.assertEqual(Submission.objects.all().count(), 4)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 10)
        self.logout()

    def test_correctly_finish_chain(self):
        self.init_competition(self.competitions[3], self.alice)
        self.login(self.alice)
        response = self._send_solution(self.ctask1, "42")
        self.assertEqual(Submission.objects.all().count(), 1)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 1)
        response = self._send_solution(self.ctask2, "42")
        self.assertEqual(Submission.objects.all().count(), 2)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 11)
        response = self._send_solution(self.ctask3, "42")
        self.assertEqual(Submission.objects.all().count(), 3)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 1111)
        self.logout()

    def test_incorrectly_finish_chain(self):
        self.init_competition(self.competitions[3], self.alice)
        self.login(self.alice)
        response = self._send_solution(self.ctask1, "-5")
        response = self._send_solution(self.ctask1, "-4")
        response = self._send_solution(self.ctask1, "-3")
        self.assertEqual(Submission.objects.all().count(), 3)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 0)
        response = self._send_solution(self.ctask2, "42")
        self.assertEqual(Submission.objects.all().count(), 4)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 10)
        response = self._send_solution(self.ctask3, "42")
        self.assertEqual(Submission.objects.all().count(), 5)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 110)
        self.logout()

    def test_nonadmin_cannot_delete_solution(self):
        self.init_competition(self.competitions[3], self.alice)
        self.login(self.alice)
        response = self._send_solution(self.ctask1, "42")
        response = self._delete_solution(self.ctask1, 1)
        self.assertEqual(Submission.objects.all().count(), 1)
        self.logout()

    def test_admin_delete_solution(self):
        self.init_competition(self.competitions[3], self.admin)
        self.login(self.admin)
        response = self._send_solution(self.ctask1, "42")
        response = self._delete_solution(self.ctask1, 1)
        self.assertEqual(Submission.objects.all().count(), 0)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 0)
        self.logout()

    # TODO: Test submission with frozen scoreboard.
