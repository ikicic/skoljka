from django.contrib.auth.models import User
from django.test import TestCase

from competition.models import Competition, CompetitionTask, Chain, \
        Submission, Team
from competition.utils import refresh_teams_cache_score, \
        update_score_on_ctask_action
from mathcontent.models import MathContent
from task.models import Task

import datetime

def create_ctask(author, competition, chain, descriptor, score):
    # TODO: make a test util for creating tasks
    content = MathContent.objects.create(text="Test text", html="Test text")
    task = Task.objects.create(name="Test task", content=content,
            author=author, hidden=True)
    chain_position = CompetitionTask.objects.filter(chain=chain).count()
    return CompetitionTask.objects.create(competition=competition, task=task,
            descriptor=descriptor, score=score, chain=chain,
            chain_position=chain_position)

CHAIN_BONUS_SCORE = 1000000
HOUR = datetime.timedelta(hours=1)
MINUTE = datetime.timedelta(minutes=1)


class CompetitionUtilsTest(TestCase):
    fixtures = ['apps/userprofile/fixtures/test_userprofiles.json']

    def setUp(self):
        # TODO: make a base class for users
        self.admin = User.objects.get(id=1)
        self.alice = User.objects.get(id=2)
        self.now = datetime.datetime.now()
        self.competition = Competition.objects.create(
                name="Test competition", hidden=False,
                registration_open_date=self.now - 50 * HOUR,
                start_date=self.now - 3 * HOUR,
                scoreboard_freeze_date=self.now + 2 * HOUR,
                end_date=self.now + 3 * HOUR)
        self.team = Team.objects.create(name="Test team", author=self.alice,
                competition=self.competition)
        self.chain = Chain.objects.create(competition=self.competition,
                name="Test chain", bonus_score=1000)
        self.ctask1 = create_ctask(self.admin, self.competition, self.chain, "42", 1)
        self.ctask2 = create_ctask(self.admin, self.competition, self.chain, "42", 10)
        self.ctask3 = create_ctask(self.admin, self.competition, self.chain, "42", 100)

    def set_freeze_date(self, freeze_date):
        self.competition.scoreboard_freeze_date = freeze_date
        self.competition.save()
        self.before_freeze = freeze_date - 10 * MINUTE
        self.after_freeze = freeze_date + 10 * MINUTE

    def simulate_submissions(self, submissions):
        team = self.team
        for ctask, date, is_correct, expected_score_triple in submissions:
            result = "42" if is_correct else "0"
            submission = Submission.objects.create(ctask=ctask, team=team,
                    date=date, result=result, cache_is_correct=is_correct)
            update_score_on_ctask_action(self.competition, team, self.chain,
                    ctask, submission, False)
            score_triple = (team.cache_score_before_freeze,
                    team.cache_score, team.cache_max_score_after_freeze)
            self.assertEqual(score_triple, expected_score_triple)

            refresh_teams_cache_score([team])
            score_triple = (team.cache_score_before_freeze,
                    team.cache_score, team.cache_max_score_after_freeze)
            self.assertEqual(score_triple, expected_score_triple)

    def test_refresh_score_no_submissions(self):
        self.set_freeze_date(self.now)
        refresh_teams_cache_score([self.team])
        self.assertEqual(self.team.cache_score, 0)
        self.assertEqual(self.team.cache_score_before_freeze, 0)
        self.assertEqual(self.team.cache_max_score_after_freeze, 0)

    def test_without_freeze(self):
        self.set_freeze_date(self.now + 5 * MINUTE)
        self.simulate_submissions([
                (self.ctask1, self.before_freeze, False, (0, 0, 0)),
                (self.ctask1, self.before_freeze, True, (1, 1, 1)),
                (self.ctask1, self.before_freeze, True, (1, 1, 1)),
                (self.ctask2, self.before_freeze, True, (11, 11, 11)),
                (self.ctask2, self.before_freeze, False, (11, 11, 11)),
                (self.ctask3, self.before_freeze, True, (1111, 1111, 1111)),
        ])

    def test_with_freeze(self):
        self.set_freeze_date(self.now - 5 * MINUTE)
        self.simulate_submissions([
                (self.ctask1, self.before_freeze, True, (1, 1, 1)),
                (self.ctask1, self.after_freeze, False, (1, 1, 1)),
                (self.ctask1, self.after_freeze, True, (1, 1, 1)),
                (self.ctask2, self.after_freeze, False, (1, 1, 11)),
                (self.ctask2, self.after_freeze, True, (1, 11, 11)),
                (self.ctask3, self.after_freeze, False, (1, 11, 1111)),
                (self.ctask3, self.after_freeze, True, (1, 1111, 1111)),
        ])
