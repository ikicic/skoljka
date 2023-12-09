import re

from skoljka.competition.models import Team
from skoljka.competition.tests.test_views import CompetitionViewsTestBase
from skoljka.competition.utils import comp_url

TEAM_CATEGORIES = '{"hr": {"1": "Crvena", "2": "Zelena", "3": "Plava"}, "en": {"1": "Red", "2": "Green", "3": "Blue"}}'


class TeamListAdminTest(CompetitionViewsTestBase):
    def init_competition(self, competition):
        competition.team_categories = TEAM_CATEGORIES
        competition.save()
        self.competition = competition
        self.team1 = Team.objects.create(
            name="Team 1", author=self.user1, competition=competition, category=1
        )
        self.team2 = Team.objects.create(
            name="Team 2", author=self.user2, competition=competition, category=2
        )

    def test_team_list_admin_confirm(self):
        self.init_competition(self.active_competition)

        # Permission test.
        self.login(self.team1.author)
        response = self.comp_post('team/list/admin/', {})
        self.assertResponse(
            response, 403, "No permission to view this competition or do this action!"
        )

        # Test OK path.
        self.login(self.admin)
        post = {
            'team-{}-category'.format(self.team1.id): '2',
            'team-{}-category'.format(self.team2.id): '3',
        }
        response = self.comp_post('team/list/admin/confirm/', post)
        self.assertResponse(response, 200)

        # Test bad request.
        post = {
            'team-{}-category'.format(self.team1.id): 'abcdef',
            'team-{}-category'.format(self.team2.id): '3',
        }
        response = self.comp_post('team/list/admin/confirm/', post)
        self.assertResponse(response, 400)

        # Test bad team_categories #1.
        self.competition.team_categories = 'INVALID'
        self.competition.save()
        post = {
            'team-{}-category'.format(self.team1.id): 'abcdef',
            'team-{}-category'.format(self.team2.id): '3',
        }
        response = self.comp_post('team/list/admin/confirm/', post)
        self.assertResponse(response, 200, "Competition has no valid team_categories.")

        # Test bad team_categories #2.
        self.competition.team_categories = '{}'
        self.competition.save()
        post = {
            'team-{}-category'.format(self.team1.id): 'abcdef',
            'team-{}-category'.format(self.team2.id): '3',
        }
        response = self.comp_post('team/list/admin/confirm/', post)
        REGEX = re.compile(r"^Team categories for the language '.*' not specified\.$")
        self.assertResponse(response, 200, REGEX)

    def test_team_list_admin(self):
        self.init_competition(self.active_competition)

        # Permission test.
        self.login(self.team1.author)
        response = self.comp_post('team/list/admin/', {})
        self.assertResponse(
            response, 403, "No permission to view this competition or do this action!"
        )

        # Test OK path.
        self.login(self.admin)
        self.assertEqual(self.team1.category, 1)
        self.assertEqual(self.team2.category, 2)
        post = {
            'team-{}-category'.format(self.team1.id): '2',
            # Accepts undefined categories.
            'team-{}-category'.format(self.team2.id): '100',
            # Unknown teams are ignored.
            'team-12314-category': '123',
        }
        response = self.comp_post('team/list/admin/', post)
        self.assertRedirects(response, comp_url(self.competition, 'team/list/admin'))
        self.assertEqual(Team.objects.get(id=self.team1.id).category, 2)
        self.assertEqual(Team.objects.get(id=self.team2.id).category, 100)
