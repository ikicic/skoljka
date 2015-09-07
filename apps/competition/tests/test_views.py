from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import Client

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

    # TODO: Test submission with frozen scoreboard.
