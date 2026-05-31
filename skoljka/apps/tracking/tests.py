from django.test import TestCase

from skoljka.apps.tracking.models import Bookmark, FavoriteProblemList, FavoriteSource, Like, Submission
from skoljka.tests.factories import make_list, make_problem, make_source, make_user


class ToggleSolvedTest(TestCase):
    def setUp(self):
        self.user = make_user(username="solver")
        self.problem = make_problem()
        self.url = f"/tracking/{self.problem.id}/solve/"

    def test_anon_returns_401(self):
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 401)

    def test_get_does_not_toggle(self):
        self.client.force_login(self.user)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)
        self.assertFalse(Submission.objects.filter(user=self.user, problem=self.problem).exists())

    def test_first_post_marks_solved(self):
        self.client.force_login(self.user)
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 200)
        sub = Submission.objects.get(user=self.user, problem=self.problem)
        self.assertTrue(sub.solved)
        self.assertIsNotNone(sub.solved_at)

    def test_second_post_unmarks_solved(self):
        self.client.force_login(self.user)
        self.client.post(self.url)
        self.client.post(self.url)
        sub = Submission.objects.get(user=self.user, problem=self.problem)
        self.assertFalse(sub.solved)
        self.assertIsNone(sub.solved_at)

    def test_re_renders_actions_fragment(self):
        self.client.force_login(self.user)
        r = self.client.post(self.url)
        self.assertContains(r, "problem-actions")
        self.assertContains(r, "Solved")

    def test_unknown_id_404(self):
        self.client.force_login(self.user)
        r = self.client.post("/tracking/999999/solve/")
        self.assertEqual(r.status_code, 404)

    def test_inaccessible_problem_404(self):
        owner = make_user(username="private-owner")
        private = make_problem(is_public=False, created_by=owner)
        self.client.force_login(self.user)
        r = self.client.post(f"/tracking/{private.pk}/solve/")
        self.assertEqual(r.status_code, 404)
        self.assertFalse(Submission.objects.filter(user=self.user, problem=private).exists())


class ToggleBookmarkTest(TestCase):
    def setUp(self):
        self.user = make_user(username="bm")
        self.problem = make_problem()
        self.url = f"/tracking/{self.problem.id}/bookmark/"

    def test_anon_returns_401(self):
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 401)

    def test_get_does_not_toggle(self):
        self.client.force_login(self.user)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)
        self.assertFalse(Bookmark.objects.filter(user=self.user, problem=self.problem).exists())

    def test_toggle_creates_then_deletes(self):
        self.client.force_login(self.user)
        self.client.post(self.url)
        self.assertTrue(
            Bookmark.objects.filter(user=self.user, problem=self.problem).exists()
        )
        self.client.post(self.url)
        self.assertFalse(
            Bookmark.objects.filter(user=self.user, problem=self.problem).exists()
        )

    def test_repeated_toggles_no_unique_violation(self):
        self.client.force_login(self.user)
        for _ in range(5):
            r = self.client.post(self.url)
            self.assertEqual(r.status_code, 200)

    def test_unknown_id_404(self):
        self.client.force_login(self.user)
        r = self.client.post("/tracking/999999/bookmark/")
        self.assertEqual(r.status_code, 404)


class ToggleLikeTest(TestCase):
    def setUp(self):
        self.user = make_user(username="lk")
        self.problem = make_problem()
        self.url = f"/tracking/{self.problem.id}/like/"

    def test_anon_returns_401(self):
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 401)

    def test_get_does_not_toggle(self):
        self.client.force_login(self.user)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)
        self.assertFalse(Like.objects.filter(user=self.user, problem=self.problem).exists())

    def test_toggle_creates_then_deletes(self):
        self.client.force_login(self.user)
        self.client.post(self.url)
        self.assertTrue(Like.objects.filter(user=self.user, problem=self.problem).exists())
        self.client.post(self.url)
        self.assertFalse(Like.objects.filter(user=self.user, problem=self.problem).exists())

    def test_like_count_in_fragment(self):
        u2 = make_user(username="lk2")
        Like.objects.create(user=u2, problem=self.problem)
        self.client.force_login(self.user)
        r = self.client.post(self.url)
        # After this user also likes: count should be 2.
        self.assertContains(r, "Liked")
        self.assertContains(r, "(2)")

    def test_unknown_id_404(self):
        self.client.force_login(self.user)
        r = self.client.post("/tracking/999999/like/")
        self.assertEqual(r.status_code, 404)


class ToggleFavoriteSourceTest(TestCase):
    def setUp(self):
        self.user = make_user(username="favs")
        self.source = make_source(slug="fav-src", name="Favorite Source")
        self.url = f"/tracking/sources/{self.source.pk}/favorite/"

    def test_anon_returns_401(self):
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 401)

    def test_get_does_not_toggle(self):
        self.client.force_login(self.user)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)
        self.assertFalse(FavoriteSource.objects.filter(user=self.user, source=self.source).exists())

    def test_inaccessible_source_404(self):
        owner = make_user(username="source-owner")
        source = make_source(slug="private-source-fav", is_public=False, created_by=owner)
        self.client.force_login(self.user)
        r = self.client.post(f"/tracking/sources/{source.pk}/favorite/")
        self.assertEqual(r.status_code, 404)
        self.assertFalse(FavoriteSource.objects.filter(user=self.user, source=source).exists())

    def test_toggle_creates_then_deletes(self):
        self.client.force_login(self.user)
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(FavoriteSource.objects.filter(user=self.user, source=self.source).exists())
        self.assertContains(r, "status-favorite active")

        self.client.post(self.url)
        self.assertFalse(FavoriteSource.objects.filter(user=self.user, source=self.source).exists())


class ToggleFavoriteProblemListTest(TestCase):
    def setUp(self):
        self.user = make_user(username="favl")
        self.problem_list = make_list(title="Favorite List", created_by=self.user)
        self.url = f"/tracking/lists/{self.problem_list.pk}/favorite/"

    def test_anon_returns_401(self):
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 401)

    def test_get_does_not_toggle(self):
        self.client.force_login(self.user)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)
        self.assertFalse(FavoriteProblemList.objects.filter(user=self.user, problem_list=self.problem_list).exists())

    def test_inaccessible_list_404(self):
        owner = make_user(username="list-owner")
        problem_list = make_list(title="Private favorite list", created_by=owner, is_public=False)
        self.client.force_login(self.user)
        r = self.client.post(f"/tracking/lists/{problem_list.pk}/favorite/")
        self.assertEqual(r.status_code, 404)
        self.assertFalse(FavoriteProblemList.objects.filter(user=self.user, problem_list=problem_list).exists())

    def test_toggle_creates_then_deletes(self):
        self.client.force_login(self.user)
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(FavoriteProblemList.objects.filter(user=self.user, problem_list=self.problem_list).exists())
        self.assertContains(r, "status-favorite active")

        self.client.post(self.url)
        self.assertFalse(FavoriteProblemList.objects.filter(user=self.user, problem_list=self.problem_list).exists())


class SaveNoteTest(TestCase):
    def setUp(self):
        self.user = make_user(username="note")
        self.problem = make_problem()
        self.url = f"/tracking/{self.problem.id}/note/"

    def test_anon_returns_401(self):
        r = self.client.post(self.url, {"note_md": "hi"})
        self.assertEqual(r.status_code, 401)

    def test_get_does_not_save(self):
        self.client.force_login(self.user)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)
        self.assertFalse(Submission.objects.filter(user=self.user, problem=self.problem).exists())

    def test_creates_submission_if_missing(self):
        self.client.force_login(self.user)
        self.assertFalse(Submission.objects.filter(user=self.user, problem=self.problem).exists())
        r = self.client.post(self.url, {"note_md": "Idea: try induction."})
        self.assertRedirects(r, f"{self.problem.get_absolute_url()}#note-section", fetch_redirect_response=False)
        sub = Submission.objects.get(user=self.user, problem=self.problem)
        self.assertEqual(sub.note_md, "Idea: try induction.")
        self.assertIsNotNone(sub.note_updated_at)

    def test_problem_page_renders_regular_note_form(self):
        self.client.force_login(self.user)
        r = self.client.get(self.problem.get_absolute_url())

        self.assertContains(r, '<form class="note-form" method="post"', html=True)
        self.assertContains(r, f'action="{self.url}"')
        self.assertContains(r, 'name="csrfmiddlewaretoken"')
        self.assertContains(r, 'name="note_md"')
        self.assertContains(r, 'type="submit"')
        self.assertContains(r, "Save note")

    def test_empty_note_accepted(self):
        self.client.force_login(self.user)
        r = self.client.post(self.url, {"note_md": ""})
        self.assertRedirects(r, f"{self.problem.get_absolute_url()}#note-section", fetch_redirect_response=False)
        sub = Submission.objects.get(user=self.user, problem=self.problem)
        self.assertEqual(sub.note_md, "")

    def test_unknown_id_404(self):
        self.client.force_login(self.user)
        r = self.client.post("/tracking/999999/note/", {"note_md": "x"})
        self.assertEqual(r.status_code, 404)
