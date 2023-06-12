from __future__ import print_function

import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from skoljka.mathcontent.models import MathContent
from skoljka.task.models import Task

from skoljka.competition.models import Competition, CompetitionTask, Chain, \
        Submission, Team
from skoljka.competition.utils import is_ctask_comment_important, \
        update_chain_comments_cache, parse_chain_comments_cache, \
        refresh_teams_cache_score, update_score_on_ctask_action, \
        detach_ctask_from_chain, delete_chain, \
        refresh_chain_cache_is_verified, \
        update_chain_cache_is_verified, \
        refresh_ctask_cache_admin_solved_count, \
        update_ctask_cache_admin_solved_count

def create_ctask(author, competition, chain, descriptor, max_score, comment=""):
    # TODO: make a test util for creating tasks
    content = MathContent.objects.create(text="Test text", html="Test text")
    task = Task.objects.create(name="Test task", content=content,
            author=author, hidden=True)
    comment = MathContent.objects.create(text=comment, html=None)
    chain_position = CompetitionTask.objects.filter(chain=chain).count()
    return CompetitionTask.objects.create(competition=competition, task=task,
            descriptor=descriptor, max_submissions=3, max_score=max_score, chain=chain,
            chain_position=chain_position, comment=comment)

CHAIN_BONUS_SCORE = 1000000
HOUR = datetime.timedelta(hours=1)
MINUTE = datetime.timedelta(minutes=1)


def _set_up_users(self):
    self.admin = User.objects.get(id=1)
    self.alice = User.objects.get(id=2)
    self.bob = User.objects.get(id=3)


class TeamScoreTest(TestCase):
    fixtures = ['skoljka/userprofile/fixtures/test_userprofiles.json']

    def setUp(self):
        _set_up_users(self)
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
        """
        Submissions is a list of tuples:
            (ctask, date, action, expected_score_triple),
        Action can be:
            True -> sending a correct solution
            False -> sending an incorrect solution
            int x -> ID of the solution (assume 1-based).
        """
        team = self.team
        chain_ctasks = list(CompetitionTask.objects.filter(chain=self.chain))
        for index, test_case in enumerate(submissions):
            try:
                ctask, date, action, expected_score_triple = test_case
                old_chain_submissions = \
                        list(Submission.objects.filter(ctask__chain=self.chain))
                if isinstance(action, bool):
                    is_correct = action
                    result = "42" if is_correct else "0"
                    submission = Submission.objects.create(ctask=ctask,
                            team=team, date=date, result=result,
                            score=is_correct * ctask.max_score)
                else:
                    # Raise an exception if not found.
                    submission = Submission.objects.get(id=action)
                    submission.delete()
                new_chain_submissions = \
                        list(Submission.objects.filter(ctask__chain=self.chain))
                update_score_on_ctask_action(
                        self.competition, team, self.chain, chain_ctasks,
                        old_chain_submissions, new_chain_submissions)
                score_triple = (team.cache_score_before_freeze,
                        team.cache_score, team.cache_max_score_after_freeze)

                refresh_teams_cache_score([team])
                score_triple = (team.cache_score_before_freeze,
                        team.cache_score, team.cache_max_score_after_freeze)
                self.assertEqual(score_triple, expected_score_triple)
            except:
                print("Test case #{}: {}".format(index, test_case))
                raise

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

    def test_admin_delete_solution(self):
        self.set_freeze_date(self.now - 5 * MINUTE)
        self.simulate_submissions([
                (self.ctask1, self.before_freeze, True, (1, 1, 1)),
                (self.ctask1, self.before_freeze, 1, (0, 0, 0)),
                (self.ctask1, self.before_freeze, False, (0, 0, 0)),
                (self.ctask1, self.before_freeze, False, (0, 0, 0)),
                (self.ctask1, self.before_freeze, 2, (0, 0, 0)),
                (self.ctask1, self.before_freeze, True, (1, 1, 1)),
        ])


class TestCompetitionTaskComments(TestCase):
    fixtures = ['skoljka/userprofile/fixtures/test_userprofiles.json']

    def setUp(self):
        _set_up_users(self)

        now = datetime.datetime.now()
        self.competition = Competition.objects.create(
                name="Test competition",
                registration_open_date=now - 50 * HOUR,
                start_date=now - 3 * HOUR,
                scoreboard_freeze_date=now + 2 * HOUR,
                end_date=now + 3 * HOUR)
        self.chain = Chain.objects.create(competition=self.competition,
                name="Test chain")

    def test_is_important(self):
        self.assertFalse(is_ctask_comment_important("nothing important here"))
        self.assertTrue(is_ctask_comment_important(
                "this is not important\n"
                "IMPORTANT: But this is very important!\n"
                "read this also"))

    def test_update_chain_comments_cache(self):
        ctasks = []
        ctasks.append(create_ctask(self.admin, self.competition, self.chain,
                "42", 1, "nothing important here"))
        ctasks.append(create_ctask(self.admin, self.competition, self.chain,
                "42", 1,
                "first nothing important\n"
                "IMPORTANT: but then something important"))
        ctasks.append(create_ctask(self.admin, self.competition, self.chain,
                "42", 1,
                "again first nothing important\n"
                "IMPORTANT: bla bla\n"
                "bla bla"))
        ctasks.append(create_ctask(self.alice, self.competition, self.chain,
                "42", 1,
                "nothing important"))
        ctasks.append(create_ctask(self.alice, self.competition, self.chain,
                "42", 1,
                "nothing important\n"
                "IMPORTANT: bla bla\n"
                "bla bla"))
        update_chain_comments_cache(self.chain, ctasks)
        num_important, num_important_my = parse_chain_comments_cache(
            self.chain, self.admin)
        self.assertEqual(num_important, 3)
        self.assertEqual(num_important_my, 2)

        num_important, num_important_my = parse_chain_comments_cache(
            self.chain, self.alice)
        self.assertEqual(num_important, 3)
        self.assertEqual(num_important_my, 1)

        num_important, num_important_my = parse_chain_comments_cache(
            self.chain, self.bob)
        self.assertEqual(num_important, 3)
        self.assertEqual(num_important_my, 0)



class ChainsTest(TestCase):
    fixtures = ['skoljka/userprofile/fixtures/test_userprofiles.json']

    def setUp(self):
        _set_up_users(self)
        self.now = datetime.datetime.now()
        self.competition = Competition.objects.create(
                name="Test competition", hidden=False,
                registration_open_date=self.now - 50 * HOUR,
                start_date=self.now - 3 * HOUR,
                scoreboard_freeze_date=self.now + 2 * HOUR,
                end_date=self.now + 3 * HOUR)
        self.chain1 = Chain.objects.create(competition=self.competition,
                name="Test chain 1", bonus_score=1000)
        self.chain2 = Chain.objects.create(competition=self.competition,
                name="Test chain 2", bonus_score=1000)

    def test_remove_ctasks_and_chains(self):
        def assertPositions(*positions):
            for id, expected in zip(ctask_ids, positions):
                ctask = CompetitionTask.objects.get(id=id)
                self.assertEqual(ctask.chain_position, expected)
                if expected == -1:
                    self.assertIsNone(ctask.chain_id)
                else:
                    self.assertIsNotNone(ctask.chain_id)

        c1 = create_ctask(self.admin, self.competition, self.chain1, "42", 1, "first")
        c2 = create_ctask(self.admin, self.competition, self.chain1, "42", 1, "second")
        c3 = create_ctask(self.admin, self.competition, self.chain1, "42", 1, "third")
        c4 = create_ctask(self.admin, self.competition, self.chain1, "42", 1, "fourth")
        d1 = create_ctask(self.admin, self.competition, self.chain2, "42", 1, "fourth")
        d2 = create_ctask(self.admin, self.competition, self.chain2, "42", 1, "fourth")
        d3 = create_ctask(self.admin, self.competition, self.chain2, "42", 1, "fourth")
        ctask_ids = [c1.id, c2.id, c3.id, c4.id, d1.id, d2.id, d3.id]

        assertPositions(0, 1, 2, 3, 0, 1, 2)

        detach_ctask_from_chain(c2)
        assertPositions(0, -1, 1, 2, 0, 1, 2)

        detach_ctask_from_chain(c4)
        assertPositions(0, -1, 1, -1, 0, 1, 2)

        detach_ctask_from_chain(c1)
        assertPositions(-1, -1, 0, -1, 0, 1, 2)

        id1 = self.chain1.id
        id2 = self.chain2.id

        delete_chain(self.chain2)
        self.assertTrue(Chain.objects.filter(id=id1).exists())
        self.assertFalse(Chain.objects.filter(id=id2).exists())
        assertPositions(-1, -1, 0, -1, -1, -1, -1)

        delete_chain(self.chain1)
        self.assertFalse(Chain.objects.filter(id=id1).exists())
        self.assertFalse(Chain.objects.filter(id=id2).exists())
        assertPositions(-1, -1, -1, -1, -1, -1, -1)

    def test_update_ctask_cache_admin_solved_count(self):
        c1 = create_ctask(self.admin, self.competition, self.chain1, "42", 1, "first")
        c2 = create_ctask(self.admin, self.competition, self.chain1, "42", 1, "second")

        self.assertEqual(c1.cache_admin_solved_count, 0)
        self.assertEqual(c2.cache_admin_solved_count, 0)

        # Submit a solution from a admin private team.
        team = Team.objects.create(name="Test team", author=self.alice,
                competition=self.competition, team_type=Team.TYPE_ADMIN_PRIVATE)
        Submission.objects.create(ctask=c1, team=team, result="42", score=c1.max_score)
        update_ctask_cache_admin_solved_count(self.competition, c1, self.chain1)
        update_ctask_cache_admin_solved_count(self.competition, c2, self.chain1)
        self.assertEqual(c1.cache_admin_solved_count, 1)
        self.assertEqual(c2.cache_admin_solved_count, 0)

        # Don't crash if no chain assigned.
        ctask = create_ctask(self.admin, self.competition, None, "42", 1, "third")
        Submission.objects.create(ctask=ctask, team=team, result="42", score=ctask.max_score)
        update_ctask_cache_admin_solved_count(self.competition, ctask, ctask.chain)

        # Regular team.
        team = Team.objects.create(name="Test team", author=self.alice,
                competition=self.competition)
        Submission.objects.create(ctask=c2, team=team, result="42", score=c2.max_score)
        update_ctask_cache_admin_solved_count(self.competition, c1, self.chain1)
        update_ctask_cache_admin_solved_count(self.competition, c2, self.chain1)
        self.assertEqual(c1.cache_admin_solved_count, 1)
        self.assertEqual(c2.cache_admin_solved_count, 0)

        # Own submissions don't count.
        team = Team.objects.create(name="Test team", author=self.admin,
                competition=self.competition, team_type=Team.TYPE_ADMIN_PRIVATE)
        Submission.objects.create(ctask=c1, team=team, result="42", score=c1.max_score)
        update_ctask_cache_admin_solved_count(self.competition, c1, self.chain1)
        update_ctask_cache_admin_solved_count(self.competition, c2, self.chain1)
        self.assertEqual(c1.cache_admin_solved_count, 1)
        self.assertEqual(c2.cache_admin_solved_count, 0)

        # Check if saved.
        self.assertEqual(CompetitionTask.objects.get(id=c1.id).cache_admin_solved_count, 1)
        self.assertEqual(CompetitionTask.objects.get(id=c2.id).cache_admin_solved_count, 0)

    def test_refresh_ctask_cache_admin_solved_count(self):
        c1 = create_ctask(self.admin, self.competition, self.chain1, "42", 1, "first")
        c2 = create_ctask(self.admin, self.competition, self.chain1, "42", 1, "second")
        c3 = create_ctask(self.admin, self.competition, self.chain1, "42", 1, "third")

        team1 = Team.objects.create(name="Test team", author=self.alice,
                competition=self.competition, team_type=Team.TYPE_ADMIN_PRIVATE)
        team2 = Team.objects.create(name="Test team", author=self.alice,
                competition=self.competition, team_type=Team.TYPE_ADMIN_PRIVATE)
        team3 = Team.objects.create(name="Test team", author=self.alice,
                competition=self.competition, team_type=Team.TYPE_ADMIN_PRIVATE)
        Submission.objects.create(ctask=c1, team=team1, result="42", score=c1.max_score)
        Submission.objects.create(ctask=c2, team=team1, result="42", score=c2.max_score)
        Submission.objects.create(ctask=c1, team=team2, result="42", score=c1.max_score)
        Submission.objects.create(ctask=c2, team=team3, result="0", score=0)

        refresh_ctask_cache_admin_solved_count(self.competition)

        self.assertEqual(CompetitionTask.objects.get(id=c1.id).cache_admin_solved_count, 2);
        self.assertEqual(CompetitionTask.objects.get(id=c2.id).cache_admin_solved_count, 1);
        self.assertEqual(CompetitionTask.objects.get(id=c3.id).cache_admin_solved_count, 0);

    def test_refresh_update_chain_cache_is_verified(self):
        self.competition.min_admin_solved_count = 1
        self.competition.save()

        c1 = create_ctask(self.admin, self.competition, self.chain1, "42", 1, "first")
        c2 = create_ctask(self.admin, self.competition, self.chain1, "42", 1, "second")

        team = Team.objects.create(name="Test team", author=self.alice,
                competition=self.competition, team_type=Team.TYPE_ADMIN_PRIVATE)
        Submission.objects.create(ctask=c1, team=team, result="42", score=c1.max_score)
        Submission.objects.create(ctask=c2, team=team, result="42", score=c2.max_score)
        self.assertFalse(self.chain1.cache_is_verified)
        refresh_ctask_cache_admin_solved_count(self.competition)
        update_chain_cache_is_verified(self.competition, self.chain1)
        self.assertTrue(self.chain1.cache_is_verified)
        self.assertTrue(Chain.objects.get(id=self.chain1.id).cache_is_verified)

        self.chain1.cache_is_verified = False
        self.chain1.save()

        self.assertFalse(Chain.objects.get(id=self.chain1.id).cache_is_verified)
        # self.chain2 is empty so it is fine.
        self.assertEqual(refresh_chain_cache_is_verified(self.competition),
                [self.chain1.id, self.chain2.id])
        self.assertTrue(Chain.objects.get(id=self.chain1.id).cache_is_verified)
