import json
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings

from skoljka.apps.accounts.challenges import _image_manifest, configured_challenges
from skoljka.apps.accounts.checks import check_registration_math_challenges
from skoljka.apps.accounts.models import User
from skoljka.apps.tracking.models import Submission
from skoljka.tests.factories import make_problem, make_staff, make_user


TEST_CHALLENGES = [{"id": "test", "tex": r"10 + \sqrt{400}", "answer": "30"}]
ROTATING_TEST_CHALLENGES = [
    {"id": "test", "tex": r"10 + \sqrt{400}", "answer": "30"},
    {"id": "other", "tex": r"7 + \sqrt{81}", "answer": "16"},
]


class RegistrationChallengeConfigTest(TestCase):
    @override_settings(REGISTRATION_MATH_CHALLENGES=TEST_CHALLENGES)
    def test_configured_challenges_are_loaded_by_id(self):
        challenges = configured_challenges()

        self.assertEqual(set(challenges), {"test"})
        self.assertEqual(challenges["test"].tex, r"10 + \sqrt{400}")
        self.assertEqual(challenges["test"].answer, "30")

    @override_settings(
        REGISTRATION_MATH_CHALLENGES=[{"id": "mul", "tex": r"2 \times 3", "answer": "6"}],
    )
    def test_accepts_different_tex_shapes(self):
        challenges = configured_challenges()

        self.assertEqual(challenges["mul"].tex, r"2 \times 3")
        self.assertEqual(challenges["mul"].answer, "6")

    @override_settings(REGISTRATION_MATH_CHALLENGES=[{"id": "bad", "tex": r"10 + \sqrt{400}", "answer": ""}])
    def test_empty_answer_is_invalid(self):
        errors = check_registration_math_challenges(None)

        self.assertEqual(errors[0].id, "accounts.E001")
        self.assertIn("non-empty answer", errors[0].msg)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    REGISTRATION_MATH_CHALLENGES=ROTATING_TEST_CHALLENGES,
)
class RegisterViewTest(TestCase):
    url = "/accounts/register/"

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.override = override_settings(REGISTRATION_MATH_CHALLENGE_DIR=self.tmp.name)
        self.override.enable()
        with open(f"{self.tmp.name}/test.png", "wb") as f:
            f.write(b"png")
        with open(f"{self.tmp.name}/other.png", "wb") as f:
            f.write(b"png")
        with open(f"{self.tmp.name}/label-email.png", "wb") as f:
            f.write(b"png")
        with open(f"{self.tmp.name}/manifest.json", "w", encoding="utf-8") as f:
            json.dump({
                "test": {"width": 124, "height": 46, "depth": 8},
                "other": {"width": 124, "height": 46, "depth": 8},
                "label-email": {"width": 68, "height": 24, "depth": 6},
            }, f)
        _image_manifest.cache_clear()

    def tearDown(self):
        self.override.disable()
        self.tmp.cleanup()

    def _post(self, data):
        self.client.get(self.url)
        challenge_id = self.client.session["registration_math_challenge_id"]
        answer = {"test": "30", "other": "16"}[challenge_id]
        data.setdefault("math_challenge", answer)
        return self.client.post(self.url, data)

    def _registration_url(self):
        body = mail.outbox[-1].body
        path = body.split("/accounts/register/continue/", 1)[1].split()[0]
        return "/accounts/register/continue/" + path

    def _registration_token_from_url(self, url):
        return url.rstrip("/").rsplit("/", 1)[1]

    def test_get_renders_form(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Register")
        self.assertContains(r, 'name="email"')
        self.assertNotContains(r, 'placeholder="Confirm password"')
        self.assertContains(r, "/accounts/register/label/email.png")
        self.assertContains(r, "/accounts/register/challenge/")

    def test_registration_label_image_is_public(self):
        r = self.client.get("/accounts/register/label/email.png")

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "image/png")

    def test_challenge_image_requires_current_session_challenge(self):
        r = self.client.get("/accounts/register/challenge/test.png")
        self.assertEqual(r.status_code, 404)

        self.client.get(self.url)
        challenge_id = self.client.session["registration_math_challenge_id"]
        r = self.client.get(f"/accounts/register/challenge/{challenge_id}.png")

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "image/png")

    def test_get_register_rotates_challenge(self):
        seen = set()
        for _ in range(10):
            self.client.get(self.url)
            seen.add(self.client.session["registration_math_challenge_id"])
            if len(seen) > 1:
                break

        self.assertGreater(len(seen), 1)

    def test_post_sends_registration_email_without_creating_user(self):
        r = self._post(
            {
                "email": "newbie@example.test",
            },
        )
        self.assertRedirects(r, "/accounts/register/sent/")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/register/continue/", mail.outbox[0].body)
        self.assertFalse(User.objects.filter(email="newbie@example.test").exists())

    def test_confirm_link_creates_user_and_logs_in(self):
        self._post({"email": "newbie@example.test"})
        url = self._registration_url()

        r = self.client.post(
            url,
            {
                "registration_token": self._registration_token_from_url(url),
                "username": "newbie",
                "password": "correct-horse-battery-staple",
                "password2": "correct-horse-battery-staple",
                "accept_terms": "on",
            },
        )

        self.assertRedirects(r, "/")
        self.assertTrue(User.objects.filter(username="newbie", email="newbie@example.test").exists())
        r2 = self.client.get("/")
        self.assertContains(r2, "newbie")

    def test_password_mismatch_rejected_on_confirmation(self):
        self._post({"email": "mm@example.test"})
        url = self._registration_url()

        r = self.client.post(
            url,
            {
                "registration_token": self._registration_token_from_url(url),
                "username": "mm",
                "password": "aaaaaaaaaa1",
                "password2": "bbbbbbbbbb1",
                "accept_terms": "on",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Passwords do not match")
        self.assertFalse(User.objects.filter(username="mm").exists())

    def test_duplicate_username_rejected(self):
        make_user(username="dup", email="dup@example.test")
        self._post({"email": "other@example.test"})
        url = self._registration_url()

        r = self.client.post(
            url,
            {
                "registration_token": self._registration_token_from_url(url),
                "username": "dup",
                "password": "correct-horse-battery-staple",
                "password2": "correct-horse-battery-staple",
                "accept_terms": "on",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "username is already taken")

    def test_existing_email_sends_account_exists_email_without_revealing_in_browser(self):
        make_user(username="first", email="same@example.test")
        r = self._post(
            {
                "email": "same@example.test",
            },
        )
        self.assertRedirects(r, "/accounts/register/sent/")
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("/accounts/register/continue/", mail.outbox[0].body)
        self.assertIn("/accounts/password-reset/", mail.outbox[0].body)

        body = mail.outbox[0].body
        path = body.split("/accounts/password-reset/", 1)[1].split()[0]
        reset_url = "/accounts/password-reset/" + path
        r = self.client.post(
            reset_url,
            {"password": "new-password-12345", "password2": "new-password-12345"},
        )

        self.assertRedirects(r, "/accounts/password-reset/done/")

    def test_missing_fields_rejected(self):
        r = self._post({"email": ""})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Email is required")

    def test_invalid_email_rejected(self):
        r = self._post({"email": "not-an-email"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "valid email")
        self.assertEqual(len(mail.outbox), 0)

    def test_terms_required_on_confirmation(self):
        self._post({"email": "terms@example.test"})
        url = self._registration_url()

        r = self.client.post(
            url,
            {
                "registration_token": self._registration_token_from_url(url),
                "username": "terms",
                "password": "correct-horse-battery-staple",
                "password2": "correct-horse-battery-staple",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "You must accept the terms of use")
        self.assertFalse(User.objects.filter(username="terms").exists())

    def test_math_challenge_required(self):
        r = self._post(
            {
                "email": "challenge@example.test",
                "math_challenge": "31",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "math challenge answer is not correct")
        self.assertEqual(len(mail.outbox), 0)

    def test_bad_confirmation_token_is_rejected(self):
        r = self.client.get("/accounts/register/continue/bad-token/")

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "invalid or has expired")


class LoginViewTest(TestCase):
    url = "/accounts/login/"

    def setUp(self):
        self.user = make_user(
            username="alice",
            email="alice@example.test",
            password="correct-horse-battery-staple",
        )

    def test_login_with_username(self):
        r = self.client.post(
            self.url, {"login": "alice", "password": "correct-horse-battery-staple"}
        )
        self.assertRedirects(r, "/")

    def test_login_with_email(self):
        r = self.client.post(
            self.url,
            {"login": "alice@example.test", "password": "correct-horse-battery-staple"},
        )
        self.assertRedirects(r, "/")

    def test_wrong_password_shows_error(self):
        r = self.client.post(self.url, {"login": "alice", "password": "nope"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Invalid")

    def test_next_redirect(self):
        r = self.client.post(
            self.url + "?next=/search/",
            {"login": "alice", "password": "correct-horse-battery-staple"},
        )
        self.assertRedirects(r, "/search/")

    def test_external_next_redirect_falls_back_to_home(self):
        r = self.client.post(
            self.url + "?next=https://example.test/",
            {"login": "alice", "password": "correct-horse-battery-staple"},
        )
        self.assertRedirects(r, "/")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetViewTest(TestCase):
    def setUp(self):
        self.user = make_user(
            username="reset-user",
            email="reset@example.test",
            password="old-password-12345",
        )

    def test_request_reset_sends_email_without_revealing_account(self):
        r = self.client.post("/accounts/password-reset/", {"email": self.user.email})

        self.assertRedirects(r, "/accounts/password-reset/sent/")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/password-reset/", mail.outbox[0].body)

    def test_request_reset_unknown_email_still_redirects(self):
        r = self.client.post("/accounts/password-reset/", {"email": "missing@example.test"})

        self.assertRedirects(r, "/accounts/password-reset/sent/")
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_confirm_changes_password(self):
        self.client.post("/accounts/password-reset/", {"email": self.user.email})
        body = mail.outbox[0].body
        path = body.split("/accounts/password-reset/", 1)[1].split()[0]
        url = "/accounts/password-reset/" + path

        r = self.client.post(
            url,
            {"password": "new-password-12345", "password2": "new-password-12345"},
        )

        self.assertRedirects(r, "/accounts/password-reset/done/")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("new-password-12345"))

    def test_reset_confirm_includes_password_manager_hints(self):
        self.client.post("/accounts/password-reset/", {"email": self.user.email})
        body = mail.outbox[0].body
        path = body.split("/accounts/password-reset/", 1)[1].split()[0]
        url = "/accounts/password-reset/" + path

        r = self.client.get(url)

        self.assertContains(r, 'autocomplete="username"')
        self.assertContains(r, 'value="reset-user"')
        self.assertContains(r, 'autocomplete="new-password"', count=2)

    def test_reset_confirm_rejects_bad_token(self):
        r = self.client.get("/accounts/password-reset/bad/token/")

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "invalid or has expired")


class LogoutViewTest(TestCase):
    def test_logout_clears_session(self):
        user = make_user(username="bye")
        self.client.force_login(user)
        r = self.client.post("/accounts/logout/")
        self.assertRedirects(r, "/")
        # Subsequent requests are anonymous.
        r2 = self.client.get("/")
        self.assertNotContains(r2, "bye")


class ProfileViewTest(TestCase):
    def setUp(self):
        self.owner = make_user(username="pablo")

    def test_public_profile_visible_to_anon(self):
        r = self.client.get(f"/accounts/profile/{self.owner.username}/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "pablo")

    def test_private_profile_hidden_from_others(self):
        self.owner.profile_public = False
        self.owner.save()
        other = make_user(username="snoop")
        self.client.force_login(other)
        r = self.client.get(f"/accounts/profile/{self.owner.username}/")
        self.assertEqual(r.status_code, 404)

    def test_private_profile_visible_to_owner(self):
        self.owner.profile_public = False
        self.owner.save()
        self.client.force_login(self.owner)
        r = self.client.get(f"/accounts/profile/{self.owner.username}/")
        self.assertEqual(r.status_code, 200)

    def test_bookmarks_section_only_for_owner(self):
        from skoljka.apps.tracking.models import Bookmark

        problem = make_problem(content="Statement")
        Bookmark.objects.create(user=self.owner, problem=problem)
        # Anonymous user: no bookmarks section.
        r = self.client.get(f"/accounts/profile/{self.owner.username}/")
        self.assertNotContains(r, "Bookmarked problems")
        # Owner: sees bookmarks section.
        self.client.force_login(self.owner)
        r = self.client.get(f"/accounts/profile/{self.owner.username}/")
        self.assertContains(r, "Bookmarked problems")

    def test_profile_pdf_buttons_require_login(self):
        from skoljka.apps.tracking.models import Bookmark, Like

        problem = make_problem(content="Statement")
        Like.objects.create(user=self.owner, problem=problem)
        Bookmark.objects.create(user=self.owner, problem=problem)

        r = self.client.get(f"/accounts/profile/{self.owner.username}/")
        self.assertNotContains(r, f"/accounts/profile/{self.owner.username}/liked/pdf/")
        self.assertNotContains(r, f"/accounts/profile/{self.owner.username}/bookmarked/pdf/")

        self.client.force_login(self.owner)
        r = self.client.get(f"/accounts/profile/{self.owner.username}/")
        self.assertContains(r, f"/accounts/profile/{self.owner.username}/liked/pdf/")
        self.assertContains(r, f"/accounts/profile/{self.owner.username}/bookmarked/pdf/")

    @patch("skoljka.apps.problems.export_views.export_problems_pdf")
    def test_liked_pdf_filters_to_visible_problems(self, export_pdf):
        from skoljka.apps.tracking.models import Like

        visible = make_problem(title="Visible")
        hidden = make_problem(title="Hidden", is_public=False, created_by=self.owner)
        Like.objects.create(user=self.owner, problem=visible)
        Like.objects.create(user=self.owner, problem=hidden)
        viewer = make_user(username="viewer")
        self.client.force_login(viewer)
        export_pdf.return_value = SimpleNamespace(filename="liked.pdf", data=b"%PDF")

        r = self.client.post(
            f"/accounts/profile/{self.owner.username}/liked/pdf/",
            {"title": "Liked", "heading_mode": "number", "action": "download"},
        )

        self.assertEqual(r.status_code, 200)
        exported_problems = export_pdf.call_args.args[0]
        self.assertEqual([p.pk for p in exported_problems], [visible.pk])

    @patch("skoljka.apps.problems.export_views.export_problems_pdf")
    def test_bookmarked_pdf_is_owner_only(self, export_pdf):
        other = make_user(username="other")
        self.client.force_login(other)

        r = self.client.get(f"/accounts/profile/{self.owner.username}/bookmarked/pdf/")

        self.assertEqual(r.status_code, 404)
        export_pdf.assert_not_called()

    def test_unknown_user_404(self):
        r = self.client.get("/accounts/profile/ghost/")
        self.assertEqual(r.status_code, 404)


class SettingsViewTest(TestCase):
    url = "/accounts/settings/"

    def test_anon_redirected_to_login(self):
        r = self.client.get(self.url)
        self.assertRedirects(r, f"/accounts/login/?next={self.url}", fetch_redirect_response=False)

    def test_post_updates_visibility(self):
        user = make_user(username="sett")
        self.client.force_login(user)
        r = self.client.post(self.url, {"profile_public": ""})
        self.assertEqual(r.status_code, 200)
        user.refresh_from_db()
        self.assertFalse(user.profile_public)


class HomeViewTest(TestCase):
    def test_anon_home(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "You have solved")
        self.assertContains(r, '<section class="home-hero-card">')
        self.assertContains(r, "Find problems by competition and year.")
        self.assertNotContains(r, '<section class="home-hero card">')

    def test_authenticated_home_hides_guest_card(self):
        user = make_user(username="hm")
        self.client.force_login(user)
        r = self.client.get("/")
        self.assertNotContains(r, '<section class="home-hero card">')

    def test_home_shows_all_visible_news(self):
        from skoljka.apps.news.models import NewsPost

        for i in range(4):
            NewsPost.objects.create(
                title=f"Visible news {i}",
                slug=f"visible-news-{i}",
                hidden=False,
            )
        NewsPost.objects.create(
            title="Visible undated news",
            slug="visible-undated-home-news",
            hidden=False,
        )
        NewsPost.objects.create(
            title="Hidden news",
            slug="hidden-home-news",
            hidden=True,
        )

        r = self.client.get("/")

        self.assertContains(r, 'class="news-list-item card"', count=5)
        self.assertNotContains(r, "<h2>News</h2>")
        for i in range(4):
            self.assertContains(r, f"Visible news {i}")
        self.assertContains(r, "Visible undated news")
        self.assertNotContains(r, "Hidden news")

    def test_home_shows_recent_and_random_public_problem_cards(self):
        make_problem(title="Public A", content="A")
        make_problem(title="Public B", content="B")
        make_problem(title="Public C", content="C")
        make_problem(title="Public D", content="D")
        make_problem(title="Private Newest", is_public=False, content="Hidden")

        r = self.client.get("/")

        self.assertContains(r, "Recently added problems")
        self.assertContains(r, "Random problems")
        self.assertContains(r, 'class="problem-card-title"', count=4)
        self.assertContains(r, "Public A")
        self.assertContains(r, "Public B")
        self.assertContains(r, "Public C")
        self.assertContains(r, "Public D")
        self.assertNotContains(r, "Private Newest")

    def test_staff_home_has_manage_news_action(self):
        staff = make_staff(username="home-news-admin")
        self.client.force_login(staff)

        r = self.client.get("/")

        self.assertContains(r, 'href="/news/manage/"')
        self.assertContains(r, ">Manage News</a>")

    def test_authenticated_home_shows_favorite_sources_and_lists(self):
        from skoljka.apps.tracking.models import FavoriteProblemList, FavoriteSource
        from skoljka.tests.factories import add_to_list, make_list, make_source

        user = make_user(username="favhome")
        source = make_source(slug="fav-source", name="Favorite Source")
        problem = make_problem(source=source, year=2024, problem_label=1)
        problem_list = make_list(title="Favorite List", created_by=user)
        add_to_list(problem_list, problem)
        Submission.objects.create(user=user, problem=problem, solved=True)
        FavoriteSource.objects.create(user=user, source=source)
        FavoriteProblemList.objects.create(user=user, problem_list=problem_list)

        self.client.force_login(user)
        r = self.client.get("/")

        self.assertContains(r, "Favorite competitions")
        self.assertContains(r, "Favorite Source")
        self.assertContains(r, "Favorite lists")
        self.assertContains(r, "Favorite List")
        self.assertContains(r, '<span class="solved-count">1</span>/1')
