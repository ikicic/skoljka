import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.test.client import Client

from skoljka.competition.models import Chain, Competition, Submission, Team, TeamMember
from skoljka.competition.tests.test_utils import create_ctask
from skoljka.permissions.constants import VIEW
from skoljka.permissions.models import ObjectPermission
from skoljka.utils.testcase import TestCase

# TODO: replace noqa F841 (local variable not used) with assertions

DAY = datetime.timedelta(days=1)
HOUR = datetime.timedelta(hours=1)
MANUAL = settings.COMPETITION_MANUAL_GRADING_TAG


def db_reload(obj):
    """Reload the given object from the database. Returns a new object."""
    return obj.__class__.objects.get(id=obj.id)


class CompetitionViewsTestBase(TestCase):
    fixtures = ['skoljka/userprofile/fixtures/test_userprofiles.json']

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
        self.alice = self.user1 = User.objects.get(id=2)
        self.bob = self.user2 = User.objects.get(id=3)
        self.client = Client()

        now = datetime.datetime.now()
        past1 = now - DAY
        past2 = past1 - DAY
        past3 = past2 - DAY
        future1 = now + DAY
        future2 = future1 + DAY
        future3 = future2 + DAY

        COMPETITION = Competition.KIND_COMPETITION
        COURSE = Competition.KIND_COURSE

        # ID, max_team_size, kind, hidden, registration_open_date,
        # start_date, end_date.
        competitions = [
            (1, 3, COMPETITION, False, future1, future2, future3),
            (2, 3, COMPETITION, False, past1, future2, future3),
            (3, 3, COMPETITION, False, past2, past1, future3),
            (4, 3, COMPETITION, False, past3, past2, past1),
            (5, 3, COMPETITION, True, past2, past1, future3),
            (6, 3, COURSE, False, past2, past1, future3),  # Course.
        ]
        competitions = [
            Competition(
                name="Test competition #{}".format(id_),
                max_team_size=team_size,
                kind=kind,
                hidden=hidden,
                registration_open_date=open_,
                start_date=start,
                end_date=end,
                scoreboard_freeze_date=end - HOUR,
            )
            for id_, team_size, kind, hidden, open_, start, end in competitions
        ]
        Competition.objects.bulk_create(competitions)
        self.competitions = {x.id: x for x in Competition.objects.all()}
        self.competition = None

    def comp_get(self, suffix, *args, **kwargs):
        """Equivalent to self.client.get with the competition's URL prepended."""
        assert self.competition
        return self.client.get(
            self.competition.get_absolute_url() + suffix, *args, **kwargs
        )

    def comp_post(self, suffix, *args, **kwargs):
        """Equivalent to self.client.post with the competition's URL prepended."""
        assert self.competition
        return self.client.get(
            self.competition.get_absolute_url() + suffix, *args, **kwargs
        )

    def create_chain(self, **kwargs):
        assert self.competition
        return Chain.objects.create(competition=self.competition, **kwargs)

    def create_ctask(self, chain, *args, **kwargs):
        """Shorthand for the global create_ctask, uses admin as author and
        self.competition as competition."""
        assert self.competition
        return create_ctask(self.admin, self.competition, chain, *args, **kwargs)


class ChainSortingTest(CompetitionViewsTestBase):
    """Test chain sorting in the public tasks view."""

    def init_competition(self, competition):
        self.competition = competition
        self.team1 = Team.objects.create(
            name="Test team 1", author=self.user1, competition=competition
        )
        TeamMember.objects.create(
            team=self.team1,
            member=self.user1,
            member_name=self.user1.username,
            invitation_status=TeamMember.INVITATION_ACCEPTED,
        )

    def test_ordering_by_category(self):
        self.init_competition(self.competitions[3])
        chain1 = self.create_chain(
            name="Chain A", category="AAA", cache_is_verified=True
        )
        chain2 = self.create_chain(
            name="Chain B", category="AAA", cache_is_verified=True
        )
        chain3 = self.create_chain(
            name="Chain C", category="AAA", cache_is_verified=True
        )
        self.create_ctask(chain1, '123', 1)
        self.create_ctask(chain2, '123', 1)
        self.create_ctask(chain3, '123', 1)
        self.login(self.alice)

        # Test that sorting by name works.
        content = self.comp_get('task/').content
        self.assertMultilineRegex(content, r'AAA.*Chain A.*Chain B.*Chain C')

        chain1.name = "Chain DA"
        chain1.save()
        content = self.comp_get('task/').content
        self.assertMultilineRegex(content, r'AAA.*Chain B.*Chain C.*Chain DA')

        # Test that sorting by category works.
        chain2.category = "BBB"
        chain2.save()
        content = self.comp_get('task/').content
        self.assertMultilineRegex(content, r'AAA.*Chain C.*Chain DA.*BBB.*Chain B')

    def test_ordering_view_locked_unlocked(self):
        self.init_competition(self.competitions[3])
        chain1 = self.create_chain(
            name="Chain A", category="AAA", cache_is_verified=True
        )
        chain2 = self.create_chain(
            name="Chain B", category="BBB", cache_is_verified=False
        )
        chain3 = self.create_chain(
            name="Chain C",
            category="AAA",
            cache_is_verified=True,
            unlock_minutes=1000000000,
        )
        self.create_ctask(chain1, '123', 1)
        self.create_ctask(chain2, '123', 1)
        self.create_ctask(chain3, '123', 1)

        # Alice should see only verified and unlocked chains.
        self.login(self.alice)
        content = self.comp_get('task/').content
        self.assertMultilineRegex(content, r'AAA.*Chain A')
        self.assertNotRegexpMatches(content, r'(BBB|Chain B|Chain C)')

        # Admin should see all verified chains.
        self.login(self.admin)
        content = self.comp_get('task/').content
        self.assertMultilineRegex(content, r'AAA.*Chain A.*Chain C')
        self.assertNotRegexpMatches(content, r'(BBB|Chain B)')

    def test_custom_ordering(self):
        self.init_competition(self.competitions[3])
        chain1 = self.create_chain(
            name="Lanac A | Chain A",
            category="[order=10] AAA | aaa",
            cache_is_verified=True,
        )
        chain2 = self.create_chain(
            name="Lanac B | Chain B",
            category="[order=30] BBB | bbb",
            cache_is_verified=True,
        )
        chain3 = self.create_chain(
            name="Lanac C | Chain C",
            category="[order=+20] CCC | ccc",
            cache_is_verified=True,
        )
        self.create_ctask(chain1, '123', 1)
        self.create_ctask(chain2, '123', 1)
        self.create_ctask(chain3, '123', 1)
        self.login(self.alice)

        assert self.competition.get_languages() == ['hr', 'en']
        # Test the first language. Note that order follows the numbers in
        # [order=...], not the category names!
        self.client.post('/i18n/setlang/', {'language': 'hr'})
        content = self.comp_get('task/').content
        self.assertMultilineRegex(content, r'AAA.*Lanac A.*CCC.*Lanac C.*BBB.*Lanac B')
        self.assertNotRegexpMatches(content, r'(aaa|bbb|ccc|Chain)')

        # Test the second language.
        self.client.post('/i18n/setlang/', {'language': 'en'})
        content = self.comp_get('task/').content
        self.assertMultilineRegex(content, r'aaa.*Chain A.*ccc.*Chain C.*bbb.*Chain B')
        self.assertNotRegexpMatches(content, r'(AAA|BBB|CCC|Lanac)')

    def test_different_ordering_for_different_languages(self):
        self.init_competition(self.competitions[3])
        chain1 = self.create_chain(
            name="Lanac A | Chain A",
            category="[order=10] AAA | [order=-10] aaa",
            cache_is_verified=True,
        )
        chain2 = self.create_chain(
            name="Lanac B | Chain B",
            category="[order=30] BBB | [order=-30] bbb",
            cache_is_verified=True,
        )
        chain3 = self.create_chain(
            name="Lanac C | Chain C",
            category="[order=+20] CCC | [order=-20] ccc",
            cache_is_verified=True,
        )
        self.create_ctask(chain1, '123', 1)
        self.create_ctask(chain2, '123', 1)
        self.create_ctask(chain3, '123', 1)
        self.login(self.alice)

        assert self.competition.get_languages() == ['hr', 'en']
        # Test the first language. Note that order follows the numbers in
        # [order=...], not the category names!
        self.client.post('/i18n/setlang/', {'language': 'hr'})
        content = self.comp_get('task/').content
        self.assertMultilineRegex(content, r'AAA.*Lanac A.*CCC.*Lanac C.*BBB.*Lanac B')
        self.assertNotRegexpMatches(content, r'(aaa|bbb|ccc|Chain)')

        # Test the second language.
        self.client.post('/i18n/setlang/', {'language': 'en'})
        content = self.comp_get('task/').content
        self.assertMultilineRegex(content, r'bbb.*Chain B.*ccc.*Chain C.*aaa.*Chain A')
        self.assertNotRegexpMatches(content, r'(AAA|BBB|CCC|Lanac)')


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
        ObjectPermission.objects.create(
            content_object=competition,
            permission_type=VIEW,
            group=self.alice.get_profile().private_group,
        )

        # It doesn't have to work even for admin_group if no explicit
        # permission is given. That's why we have permission system.
        # TODO: Test not finished.

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
        response = self.client.post(
            '/competition/4/registration/', {'name': "Team name"}
        )
        self.assertRedirects(response, '/competition/4/')
        self.logout()

    def test_registration_single_member(self):
        """Test registration without any additional members."""
        self.login(self.alice)
        response = self.client.post(
            '/competition/2/registration/', {'name': "Team name"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'competition_registration_complete.html')
        self.assertIsNotNone(response.context['team'])
        self.assertEqual(response.context['team'].name, "Team name")
        self.assertEqual(TeamMember.objects.all().count(), 1)
        self.logout()

    def test_registration_one_invite_and_accept(self):
        """Test full registration with two members."""
        self.login(self.alice)
        response = self.client.post(
            '/competition/2/registration/',
            {'name': "Team name", "member2_username": self.admin.username},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'competition_registration_complete.html')
        team = response.context['team']
        self.assertIsNotNone(team)
        self.assertEqual(team.name, "Team name")
        self.assertEqual(
            TeamMember.objects.filter(
                invitation_status=TeamMember.INVITATION_ACCEPTED
            ).count(),
            1,
        )
        self.assertEqual(
            TeamMember.objects.filter(
                invitation_status=TeamMember.INVITATION_UNANSWERED
            ).count(),
            1,
        )
        self.logout()

        self.login(self.admin)
        response = self.client.post(
            '/competition/2/registration/', {'invitation-accept': team.id}
        )
        self.assertIsNotNone(response.context['team'])
        self.assertEqual(
            TeamMember.objects.filter(
                invitation_status=TeamMember.INVITATION_ACCEPTED
            ).count(),
            2,
        )
        self.assertEqual(
            TeamMember.objects.filter(
                invitation_status=TeamMember.INVITATION_UNANSWERED
            ).count(),
            0,
        )
        self.logout()

    def test_same_user_in_two_competitions(self):
        """User should be able to join multiple competitions, also using the
        same team name."""
        self.login(self.alice)
        self.client.post('/competition/2/registration/', {'name': "same-name"})
        self.assertEqual(Team.objects.all().count(), 1)
        self.assertEqual(TeamMember.objects.all().count(), 1)
        response = self.client.post(
            '/competition/3/registration/', {'name': "same-name"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Team.objects.all().count(), 2)
        self.assertEqual(TeamMember.objects.all().count(), 2)

    def test_delete_invitations_after_creating_a_team(self):
        self.login(self.alice)
        self.client.post(
            '/competition/2/registration/',
            {'name': "Alice's team", "member2_username": self.bob.username},
        )
        self.assertEqual(
            TeamMember.objects.filter(team_id=1, member_id=self.bob.id).count(), 1
        )
        self.logout()
        self.login(self.bob)
        self.client.post('/competition/2/registration/', {'name': "Bob's team"})
        self.assertEqual(
            TeamMember.objects.filter(team_id=1, member_id=self.bob.id).count(), 0
        )

    def test_delete_other_invitations_after_accepting_one(self):
        """Other invitations in the same competition should be deleted after
        selecting one. Invitations from other competition shouldn't be
        affected."""
        self.login(self.alice)
        self.client.post(
            '/competition/2/registration/',
            {'name': "Alice 2", "member2_username": self.admin.username},
        )
        self.client.post(
            '/competition/3/registration/',
            {'name': "Alice 3", "member2_username": self.admin.username},
        )
        self.logout()
        self.login(self.bob)
        response = self.client.post(
            '/competition/2/registration/',
            {'name': "Bob 2", "member2_username": self.admin.username},
        )
        self.assertEqual(response.status_code, 200)
        self.logout()
        self.login(self.admin)
        self.assertEqual(TeamMember.objects.filter(team__competition_id=2).count(), 4)
        self.assertEqual(TeamMember.objects.filter(team__competition_id=3).count(), 2)
        self.client.post('/competition/2/registration/', {'invitation-accept': 1})
        self.assertEqual(TeamMember.objects.filter(team__competition_id=2).count(), 3)
        self.assertEqual(TeamMember.objects.filter(team__competition_id=3).count(), 2)

    def test_update_members(self):
        self.login(self.alice)
        # First add one user.
        self.client.post(
            '/competition/2/registration/',
            {'name': "Alice 2", "member2_username": self.bob.username},
        )
        self.assertEqual(TeamMember.objects.filter(team__competition_id=2).count(), 2)

        # Then add another.
        self.client.post(
            '/competition/2/registration/',
            {
                'name': "Alice 2",
                "member2_username": self.bob.username,
                "member3_username": self.admin.username,
            },
        )
        self.assertEqual(TeamMember.objects.filter(team__competition_id=2).count(), 3)

        # Then update first.
        self.client.post(
            '/competition/2/registration/',
            {
                'name': "Alice 2",
                "member2_manual": "sarma",
                "member3_username": self.admin.username,
            },
        )
        self.assertEqual(TeamMember.objects.filter(team__competition_id=2).count(), 3)
        self.assertEqual(
            set(
                TeamMember.objects.filter(team__competition_id=2).values_list(
                    'member_name', flat=True
                )
            ),
            set([self.alice.username, "sarma", self.admin.username]),
        )

        # Then delete first.
        self.client.post(
            '/competition/2/registration/',
            {'name': "Alice 2", "member3_username": self.admin.username},
        )
        self.assertEqual(TeamMember.objects.filter(team__competition_id=2).count(), 2)
        self.assertEqual(
            set(
                TeamMember.objects.filter(team__competition_id=2).values_list(
                    'member_name', flat=True
                )
            ),
            set([self.alice.username, self.admin.username]),
        )

    def test_reject_used_and_current_user(self):
        """Reject invitation if user already has a team."""
        self.login(self.alice)
        # Firstly, reject him/herself...
        self.client.post(
            '/competition/2/registration/',
            {'name': "Alice", "member2_username": self.alice.username},
        )
        self.assertEqual(Team.objects.filter(competition_id=2).count(), 0)

        # Alice invites admin.
        self.client.post(
            '/competition/2/registration/',
            {'name': "Alice", "member2_username": self.admin.username},
        )
        self.assertEqual(Team.objects.filter(competition_id=2).count(), 1)
        self.logout()

        # Admin accepts the invitation.
        self.login(self.admin)
        self.client.post(
            '/competition/2/registration/',
            {'invitation-accept': Team.objects.get(competition_id=2).id},
        )
        self.logout()

        # Bob tries to invite admin, but fails.
        self.login(self.bob)
        self.client.post(
            '/competition/2/registration/',
            {'name': "Bob", "member2_username": self.admin.username},
        )
        self.assertEqual(Team.objects.filter(competition_id=2).count(), 1)


class CourseTest(CompetitionViewsTestBase):
    def test_registration(self):
        """Course registration is simpler -- there is no team."""
        # Test registration. Check that the name kwarg is ignored.
        self.login(self.alice)
        response = self.client.post(
            '/competition/6/registration/', {'name': "should be ignored"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'competition_registration_complete_course.html'
        )
        team = Team.objects.get(competition=self.competitions[6], author=self.alice)
        self.assertEqual(team.name, self.alice.username)  # name is ignored

        # Test re-registration, should be rejected.
        response = self.client.post('/competition/6/registration/', {})
        self.assertRedirects(response, '/competition/6/')
        self.logout()

    def test_chain_new(self):
        self.login(self.admin)

        # Test that 'unlock_minutes' was replaced with 'unlock_days'.
        response = self.client.get('/competition/6/chain/new/')
        self.assertNotContains(response, 'unlock_minutes')
        self.assertContains(response, 'unlock_days')

        # Test that days are multiplied with 24*60.
        response = self.client.post(
            '/competition/6/chain/new/',
            {
                'name': "Chain-ABC",
                'category': "Category-DEF",
                'bonus_score': "2",
                'unlock_days': "14",
                'unlock_mode': "1",
                'position': "0",
            },
        )
        chain = Chain.objects.get(name="Chain-ABC")
        self.assertEqual(chain.unlock_minutes, 14 * 24 * 60)
        self.assertRedirects(response, chain.get_absolute_url())

        # Test that recovering days from minutes works.
        response = self.client.get(chain.get_absolute_url())
        self.assertContains(response, 'value="14.0"')

        self.logout()


class SubmissionTest(CompetitionViewsTestBase):
    def init_competition(self, competition, user):
        self.team = Team.objects.create(
            name="Test team", author=user, competition=competition
        )
        TeamMember.objects.create(
            team=self.team,
            member=user,
            member_name=user.username,
            invitation_status=TeamMember.INVITATION_ACCEPTED,
        )
        self.chain = Chain.objects.create(
            competition=competition, name="Test chain", bonus_score=1000
        )
        self.ctask1 = create_ctask(self.admin, competition, self.chain, "42", 1)
        self.ctask2 = create_ctask(self.admin, competition, self.chain, "42", 10)
        self.ctask3 = create_ctask(self.admin, competition, self.chain, "42", 100)

    def _send_solution(self, task, result):
        return self.client.post(task.get_absolute_url(), {'result': result})

    def _delete_solution(self, task, submission_id):
        return self.client.post(
            task.get_absolute_url(), {'delete-submission': submission_id}
        )

    def test_before_contest_start(self):
        self.init_competition(self.competitions[2], self.alice)
        self.login(self.alice)
        response = self._send_solution(self.ctask1, "-5")
        self.assertEqual(response.status_code, 404)
        self.logout()

    def test_after_contest_end(self):
        self.init_competition(self.competitions[4], self.alice)
        self.login(self.alice)
        response = self._send_solution(self.ctask1, "42")  # noqa: F841
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

    def test_unlock_if_try_limit_exceeded(self):
        self.init_competition(self.competitions[3], self.alice)
        self.login(self.alice)
        response = self._send_solution(self.ctask1, "-5")  # noqa: F841
        response = self._send_solution(self.ctask1, "-4")  # noqa: F841
        response = self._send_solution(self.ctask1, "-3")  # noqa: F841
        self.assertEqual(Submission.objects.all().count(), 3)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 0)
        response = self._send_solution(self.ctask2, "42")  # noqa: F841
        self.assertEqual(Submission.objects.all().count(), 4)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 10)
        self.logout()

    def test_correctly_finish_chain(self):
        self.init_competition(self.competitions[3], self.alice)
        self.login(self.alice)
        response = self._send_solution(self.ctask1, "42")  # noqa: F841
        self.assertEqual(Submission.objects.all().count(), 1)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 1)
        response = self._send_solution(self.ctask2, "42")  # noqa: F841
        self.assertEqual(Submission.objects.all().count(), 2)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 11)
        response = self._send_solution(self.ctask3, "42")  # noqa: F841
        self.assertEqual(Submission.objects.all().count(), 3)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 1111)
        self.logout()

    def test_incorrectly_finish_chain(self):
        self.init_competition(self.competitions[3], self.alice)
        self.login(self.alice)
        response = self._send_solution(self.ctask1, "-5")  # noqa: F841
        response = self._send_solution(self.ctask1, "-4")  # noqa: F841
        response = self._send_solution(self.ctask1, "-3")  # noqa: F841
        self.assertEqual(Submission.objects.all().count(), 3)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 0)
        response = self._send_solution(self.ctask2, "42")  # noqa: F841
        self.assertEqual(Submission.objects.all().count(), 4)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 10)
        response = self._send_solution(self.ctask3, "42")  # noqa: F841
        self.assertEqual(Submission.objects.all().count(), 5)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 110)
        self.logout()

    def test_nonadmin_cannot_delete_solution(self):
        self.init_competition(self.competitions[3], self.alice)
        self.login(self.alice)
        response = self._send_solution(self.ctask1, "42")  # noqa: F841
        response = self._delete_solution(self.ctask1, 1)  # noqa: F841
        self.assertEqual(Submission.objects.all().count(), 1)
        self.logout()

    def test_admin_delete_solution(self):
        self.init_competition(self.competitions[3], self.admin)
        self.login(self.admin)
        response = self._send_solution(self.ctask1, "42")  # noqa: F841
        response = self._delete_solution(self.ctask1, 1)  # noqa: F841
        self.assertEqual(Submission.objects.all().count(), 0)
        self.assertEqual(Team.objects.get(id=self.team.id).cache_score, 0)
        self.logout()

    # TODO: Test submission with frozen scoreboard.


class ManualGradingTest(CompetitionViewsTestBase):
    def init_competition(self, competition):
        self.competition = competition
        self.team1 = Team.objects.create(
            name="Test team 1", author=self.user1, competition=competition
        )
        self.team2 = Team.objects.create(
            name="Test team 2", author=self.user2, competition=competition
        )
        TeamMember.objects.create(
            team=self.team1,
            member=self.user1,
            member_name=self.user1.username,
            invitation_status=TeamMember.INVITATION_ACCEPTED,
        )
        TeamMember.objects.create(
            team=self.team2,
            member=self.user2,
            member_name=self.user2.username,
            invitation_status=TeamMember.INVITATION_ACCEPTED,
        )
        chain1 = Chain.objects.create(competition=competition, name="Test chain 1")
        chain2 = Chain.objects.create(competition=competition, name="Test chain 2")
        self.ctask1 = create_ctask(self.admin, competition, chain1, MANUAL, 1)
        self.ctask2 = create_ctask(self.admin, competition, chain2, MANUAL, 10)

    def send_manual_solution(self, task, answer):
        """Send a manual answer and return the new submission object."""
        response = self.client.post(task.get_absolute_url(), {'text': answer})
        self.assertIsInstance(response, HttpResponseRedirect)
        return Submission.objects.all().order_by('-id')[0]

    def test_marking_as_read_and_unread(self):
        self.init_competition(self.competitions[3])

        self.login(self.user1)
        sub1 = self.send_manual_solution(self.ctask1, "answer 1 by user 1")
        self.send_manual_solution(self.ctask2, "answer 2 by user 1")

        self.login(self.user2)
        self.send_manual_solution(self.ctask1, "answer 1 by user 2")

        # Test that a non-admin cannot view the submission detail admin page.
        self.assertEqual(self.client.get(sub1.get_admin_url()).status_code, 403)
        self.assertEqual(
            self.client.post(sub1.get_admin_url(), {'mark_new': 0}).status_code, 403
        )

        # Test current values of counters.
        self.login(self.admin)
        self.assertEqual(db_reload(self.ctask1).cache_new_activities_count, 2)
        self.assertEqual(db_reload(self.ctask2).cache_new_activities_count, 1)

        # Test marking as read.
        self.client.post(sub1.get_admin_url(), {'mark_new': 0})
        self.assertEqual(db_reload(self.ctask1).cache_new_activities_count, 1)
        self.assertEqual(db_reload(self.ctask2).cache_new_activities_count, 1)

        # Test marking as unread.
        self.client.post(sub1.get_admin_url(), {'mark_new': 1})
        self.assertEqual(db_reload(self.ctask1).cache_new_activities_count, 2)
        self.assertEqual(db_reload(self.ctask2).cache_new_activities_count, 1)

        # Test refreshing the cache.
        self.ctask1.cache_new_activities_count = 10
        self.ctask1.save()
        self.assertEqual(db_reload(self.ctask1).cache_new_activities_count, 10)
        self.client.post(
            self.competition.get_absolute_url() + 'chain/tasks/',
            {'action': 'refresh-ctask-cache-new-activities-count'},
        )
        self.assertEqual(db_reload(self.ctask1).cache_new_activities_count, 2)
        self.assertEqual(db_reload(self.ctask2).cache_new_activities_count, 1)
