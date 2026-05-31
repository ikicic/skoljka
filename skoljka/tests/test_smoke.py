"""Cross-cutting smoke tests."""

from django.test import TestCase

from skoljka.apps.tags.cache import tag_api_url
from skoljka.tests.factories import make_list, make_problem, make_source, make_staff, make_tag, make_user


class PublicUrlSmokeTest(TestCase):
    """GET every publicly-accessible URL and assert the expected status code."""

    @classmethod
    def setUpTestData(cls):
        cls.src = make_source(slug="imo", name="IMO")
        cls.tag = make_tag(slug="algebra", name="Algebra")
        cls.problem = make_problem(
            title="P1", source=cls.src, year=2024, problem_label=1,
            content="Statement",
        )
        cls.problem.tags.add(cls.tag)
        cls.list = make_list(title="PubList", is_public=True)
        cls.user = make_user(username="smoke", password="correct-horse-battery-staple")
        cls.staff = make_staff(username="staff-smoke", password="correct-horse-battery-staple")

    def _assert_ok(self, path):
        r = self.client.get(path)
        self.assertEqual(r.status_code, 200, f"GET {path} -> {r.status_code}")

    def test_anon_reachable_urls(self):
        for url in [
            "/",
            "/accounts/login/",
            "/accounts/register/",
            "/accounts/about/",
            "/accounts/privacy/",
            "/accounts/terms/",
            "/archive/",
            f"/archive/{self.src.slug}/",
            "/problems/",
            f"/problems/{self.problem.id}/",
            tag_api_url("en"),
            "/search/",
            "/lists/",
            f"/lists/{self.list.pk}/",
            f"/accounts/profile/{self.user.username}/",
        ]:
            self._assert_ok(url)

    def test_anon_redirects(self):
        # Settings, list_create require login -> 302.
        for url in ["/accounts/settings/", "/lists/new/"]:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, f"{url} expected 302")

    def test_anon_staff_gates(self):
        # Contextual staff endpoints redirect anon to login.
        for url in [
            "/archive/manage/",
            "/archive/manage/new/",
            "/problems/manage/",
            "/problems/manage/new/",
            "/problems/import/pdf/",
        ]:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, f"{url} expected 302")
            self.assertIn("/accounts/login/", r.url)

    def test_regular_user_staff_gates_return_403(self):
        self.client.force_login(self.user)
        for url in [
            "/archive/manage/new/",
            "/problems/manage/new/",
            "/problems/import/pdf/",
        ]:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 403, f"{url} expected 403")

    def test_staff_nav_admin_points_to_django_admin(self):
        self.client.force_login(self.staff)
        r = self.client.get("/")
        self.assertContains(r, 'href="/admin/"')
        self.assertNotContains(r, "admin-panel")

    def test_custom_admin_panel_removed(self):
        r = self.client.get("/admin-panel/")
        self.assertEqual(r.status_code, 404)


class CsrfEnforcedOnHtmxEndpointTest(TestCase):
    """HTMX POST endpoints must reject requests without a CSRF token."""

    def test_tracking_post_without_csrf_rejected(self):
        user = make_user(username="csrf")
        problem = make_problem()
        # enforce_csrf_checks=True disables the test client's CSRF bypass.
        client = self.client_class(enforce_csrf_checks=True)
        client.force_login(user)
        r = client.post(f"/tracking/{problem.id}/solve/")
        self.assertEqual(r.status_code, 403)
