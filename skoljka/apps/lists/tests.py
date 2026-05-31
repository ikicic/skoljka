from types import SimpleNamespace
from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase

from skoljka.apps.lists.models import ProblemList, ProblemListItem
from skoljka.apps.tracking.models import Submission
from skoljka.tests.factories import (
    add_to_list,
    make_list,
    make_problem,
    make_source,
    make_tag,
    make_user,
)


class ListIndexViewTest(TestCase):
    def setUp(self):
        self.alice = make_user(username="a")
        self.bob = make_user(username="b")
        self.alice_pub = make_list(title="AlicePub", created_by=self.alice, is_public=True)
        self.alice_priv = make_list(title="AlicePriv", created_by=self.alice, is_public=False)
        self.bob_pub = make_list(title="BobPub", created_by=self.bob, is_public=True)

    def test_anon_sees_only_public(self):
        r = self.client.get("/lists/")
        self.assertContains(r, "AlicePub")
        self.assertContains(r, "BobPub")
        self.assertNotContains(r, "AlicePriv")
        self.assertNotContains(r, "My Lists")
        self.assertContains(r, '<div class="section-card">')
        self.assertNotContains(r, '<div class="section-card card">')
        self.assertNotContains(r, "favorite-toggle")

    def test_authenticated_sees_my_and_public(self):
        self.client.force_login(self.alice)
        r = self.client.get("/lists/")
        self.assertContains(r, "My Lists")
        self.assertContains(r, "AlicePub")
        self.assertContains(r, "AlicePriv")
        self.assertContains(r, "BobPub")
        self.assertContains(r, 'class="table problem-list-table"', count=2)
        self.assertContains(r, '<div class="section-card">', count=2)
        self.assertNotContains(r, '<div class="section-card card">')
        self.assertContains(r, "<th>Name</th>")
        self.assertContains(r, '<th class="col-progress">Solved</th>')
        self.assertContains(r, 'class="favorite-col"')
        self.assertContains(r, f'hx-post="/tracking/lists/{self.bob_pub.pk}/favorite/"')

    def test_shows_visible_problem_counts(self):
        visible = make_problem(title="Visible problem", is_public=True)
        hidden = make_problem(title="Hidden problem", is_public=False, created_by=self.bob)
        add_to_list(self.bob_pub, visible)
        add_to_list(self.bob_pub, hidden)

        r = self.client.get("/lists/")
        self.assertContains(r, "BobPub")
        self.assertContains(r, '<span class="progress-text">1</span>')
        self.assertNotContains(r, '<span class="progress-text">2</span>')

    def test_owner_count_includes_private_problems(self):
        hidden = make_problem(title="Alice hidden", is_public=False, created_by=self.alice)
        add_to_list(self.alice_priv, hidden)

        self.client.force_login(self.alice)
        r = self.client.get("/lists/")
        self.assertContains(r, "AlicePriv")
        self.assertContains(r, '<span class="progress-text"><span class="solved-count">0</span>/1</span>')

    def test_authenticated_shows_solved_progress(self):
        solved = make_problem(title="Solved problem", is_public=True)
        unsolved = make_problem(title="Unsolved problem", is_public=True)
        add_to_list(self.bob_pub, solved)
        add_to_list(self.bob_pub, unsolved)
        Submission.objects.create(user=self.alice, problem=solved, solved=True)

        self.client.force_login(self.alice)
        r = self.client.get("/lists/")

        self.assertContains(r, '<span class="progress-text"><span class="solved-count">1</span>/2</span>')
        self.assertContains(r, 'class="progress-bar-fill" style="width:50%"')

    def test_authenticated_sees_new_list_action_without_page_title(self):
        self.client.force_login(self.alice)
        r = self.client.get("/lists/")
        self.assertContains(r, 'class="page-actions"')
        self.assertContains(r, 'href="/lists/new/"')
        self.assertContains(r, ">New list</a>")
        self.assertNotContains(r, "<h1>Problem Lists</h1>")

    def test_anon_does_not_see_new_list_action(self):
        r = self.client.get("/lists/")
        self.assertNotContains(r, 'class="page-actions"')
        self.assertNotContains(r, 'href="/lists/new/"')


class ListDetailViewTest(TestCase):
    def setUp(self):
        self.owner = make_user(username="own")
        self.other = make_user(username="oth")
        self.private = make_list(
            title="Hidden list", created_by=self.owner, is_public=False
        )

    def test_owner_sees_private(self):
        self.client.force_login(self.owner)
        r = self.client.get(f"/lists/{self.private.pk}/")
        self.assertEqual(r.status_code, 200)

    def test_pdf_export_button_requires_login(self):
        visible = make_problem(title="Visible")
        public_list = make_list(title="Public PDF", created_by=self.owner, is_public=True)
        add_to_list(public_list, visible)

        r = self.client.get(f"/lists/{public_list.pk}/")
        self.assertNotContains(r, f"/lists/{public_list.pk}/pdf/")

        self.client.force_login(self.other)
        r = self.client.get(f"/lists/{public_list.pk}/")
        self.assertContains(r, f"/lists/{public_list.pk}/pdf/")

    @patch("skoljka.apps.problems.export_views.export_problems_pdf")
    def test_pdf_export_preserves_order_and_filters_private_problems(self, export_pdf):
        export_pdf.return_value = SimpleNamespace(filename="ordered.pdf", data=b"%PDF")
        first = make_problem(title="First", is_public=True)
        hidden = make_problem(title="Hidden", is_public=False, created_by=self.owner)
        second = make_problem(title="Second", is_public=True)
        public_list = make_list(title="Ordered PDF", created_by=self.owner, is_public=True)
        add_to_list(public_list, first)
        add_to_list(public_list, hidden)
        add_to_list(public_list, second)

        self.client.force_login(self.other)
        r = self.client.post(f"/lists/{public_list.pk}/pdf/", {"title": "Ordered PDF", "heading_mode": "number", "action": "download"})

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        problems = export_pdf.call_args.args[0]
        self.assertEqual([p.pk for p in problems], [first.pk, second.pk])

    def test_non_owner_no_token_404(self):
        self.client.force_login(self.other)
        r = self.client.get(f"/lists/{self.private.pk}/")
        self.assertEqual(r.status_code, 404)

    def test_token_does_not_grant_access(self):
        self.client.force_login(self.other)
        r = self.client.get(f"/lists/{self.private.pk}/?token=anything")
        self.assertEqual(r.status_code, 404)


class ListCreateViewTest(TestCase):
    url = "/lists/new/"

    def test_anon_redirected_to_login(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)

    def test_post_creates_list_owned_by_user(self):
        user = make_user(username="creator")
        self.client.force_login(user)
        r = self.client.post(
            self.url, {"title": "Fresh list", "description": "desc", "public": "on"}
        )
        self.assertEqual(r.status_code, 302)
        pl = ProblemList.objects.get(title="Fresh list")
        self.assertEqual(pl.created_by, user)
        self.assertTrue(pl.is_public)


class ListEditViewTest(TestCase):
    def setUp(self):
        self.owner = make_user(username="own")
        self.other = make_user(username="oth")
        self.pl = make_list(title="Editable", created_by=self.owner)

    def test_owner_only(self):
        self.client.force_login(self.other)
        r = self.client.get(f"/lists/{self.pl.pk}/edit/")
        self.assertEqual(r.status_code, 403)

    def test_edit_renders_problem_builder(self):
        self.client.force_login(self.owner)
        r = self.client.get(f"/lists/{self.pl.pk}/edit/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'data-list-editor=""')
        self.assertContains(r, 'data-save-url="/lists/%d/items/save/"' % self.pl.pk)
        self.assertContains(r, "Save changes")
        self.assertContains(r, 'href="/lists/%d/edit/details/"' % self.pl.pk)

    def test_edit_details_updates_metadata(self):
        self.client.force_login(self.owner)
        r = self.client.post(
            f"/lists/{self.pl.pk}/edit/details/",
            {"title": "Renamed", "description": "new desc", "public": "on"},
        )
        self.assertEqual(r.status_code, 302)
        self.pl.refresh_from_db()
        self.assertEqual(self.pl.title, "Renamed")
        self.assertEqual(self.pl.description, "new desc")
        self.assertTrue(self.pl.is_public)

    def test_edit_details_requires_owner(self):
        self.client.force_login(self.other)
        r = self.client.get(f"/lists/{self.pl.pk}/edit/details/")
        self.assertEqual(r.status_code, 403)

    def test_picker_search_returns_accessible_matches(self):
        self.client.force_login(self.owner)
        source = make_source(slug="imo", name="IMO")
        tag = make_tag(slug="algebra", name="Algebra")
        problem = make_problem(title="Quadratic equations", source=source, year=2024)
        problem.tags.add(tag)
        Submission.objects.create(user=self.owner, problem=problem, solved=True)
        add_to_list(self.pl, problem)
        r = self.client.get(f"/lists/{self.pl.pk}/problem-search/?q=imo algebra")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["results"][0]["id"], problem.pk)
        self.assertTrue(data["results"][0]["already_added"])
        self.assertTrue(data["results"][0]["solved"])

    def test_edit_initial_payload_marks_solved_problems(self):
        self.client.force_login(self.owner)
        problem = make_problem(title="Solved problem")
        Submission.objects.create(user=self.owner, problem=problem, solved=True)
        add_to_list(self.pl, problem)
        r = self.client.get(f"/lists/{self.pl.pk}/edit/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '"solved": true')

    def test_picker_search_matches_source_name_prefix(self):
        self.client.force_login(self.owner)
        source = make_source(slug="imo", name="International Olympiad")
        problem = make_problem(source=source, year=2024, problem_label=1)
        r = self.client.get(f"/lists/{self.pl.pk}/problem-search/?q=Inter")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["results"][0]["id"], problem.pk)
        self.assertEqual(data["results"][0]["source"], "International Olympiad")
        self.assertEqual(data["results"][0]["source_url"], source.get_absolute_url())

    def test_picker_search_requires_edit_permission(self):
        self.client.force_login(self.other)
        r = self.client.get(f"/lists/{self.pl.pk}/problem-search/?q=test")
        self.assertEqual(r.status_code, 403)

    def test_api_save_replaces_ordered_items(self):
        self.client.force_login(self.owner)
        old = make_problem()
        p1 = make_problem()
        p2 = make_problem()
        add_to_list(self.pl, old)
        r = self.client.post(
            f"/lists/{self.pl.pk}/items/save/",
            data='{"problem_ids": [%d, %d]}' % (p2.pk, p1.pk),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(list(self.pl.items.order_by("order").values_list("order", flat=True)), [1, 2])
        self.assertEqual(
            list(self.pl.items.order_by("order").values_list("problem_id", flat=True)),
            [p2.pk, p1.pk],
        )

    def test_api_save_deduplicates_ids(self):
        self.client.force_login(self.owner)
        problem = make_problem()
        r = self.client.post(
            f"/lists/{self.pl.pk}/items/save/",
            data='{"problem_ids": [%d, %d]}' % (problem.pk, problem.pk),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.pl.items.count(), 1)

    def test_api_save_rejects_unknown_problem(self):
        self.client.force_login(self.owner)
        r = self.client.post(
            f"/lists/{self.pl.pk}/items/save/",
            data='{"problem_ids": [999999]}',
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 404)

    def test_api_save_rejects_wrong_json_shape(self):
        self.client.force_login(self.owner)
        r = self.client.post(
            f"/lists/{self.pl.pk}/items/save/",
            data='["not an object"]',
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_api_save_requires_edit_permission(self):
        self.client.force_login(self.other)
        problem = make_problem()
        r = self.client.post(
            f"/lists/{self.pl.pk}/items/save/",
            data='{"problem_ids": [%d]}' % problem.pk,
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)

    def test_bulk_edit_renders_problem_drafts(self):
        self.client.force_login(self.owner)
        tag = make_tag(slug="geometry", name="Geometry")
        problem = make_problem(title="Editable problem", created_by=self.owner, content="Old statement")
        problem.tags.add(tag)
        add_to_list(self.pl, problem)

        r = self.client.get(f"/lists/{self.pl.pk}/bulk-edit/")

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'id="list-bulk-edit"')
        self.assertContains(r, f"List: {self.pl.title}")
        self.assertContains(r, "Old statement")
        self.assertContains(r, '"slug": "geometry"')

    def test_bulk_edit_requires_problem_edit_permission(self):
        self.client.force_login(self.owner)
        problem = make_problem(title="Public problem", created_by=self.other, is_public=True)
        add_to_list(self.pl, problem)

        r = self.client.get(f"/lists/{self.pl.pk}/bulk-edit/")

        self.assertEqual(r.status_code, 403)

    def test_bulk_edit_save_updates_content_and_visible_tags(self):
        self.client.force_login(self.owner)
        old_tag = make_tag(slug="old-tag", name="Old")
        hidden_tag = make_tag(slug="hidden-technique", name="Hidden", kind="technique", hidden=True)
        new_tag = make_tag(slug="number-theory", name="Number theory")
        problem = make_problem(created_by=self.owner, content="Old statement")
        problem.tags.add(old_tag, hidden_tag)
        add_to_list(self.pl, problem)

        r = self.client.post(
            f"/lists/{self.pl.pk}/bulk-edit/save/",
            data='{"problems":[{"id":%d,"source_md":"New statement","language":"en","tags":["number-theory"],"new_tags":[]}]}' % problem.pk,
            content_type="application/json",
        )

        self.assertEqual(r.status_code, 200)
        problem.refresh_from_db()
        self.assertEqual(problem.content.get().source_for("en"), "New statement")
        self.assertEqual(
            set(problem.tags.values_list("slug", flat=True)),
            {new_tag.slug, hidden_tag.slug},
        )

    def test_bulk_edit_save_rejects_wrong_json_shape(self):
        self.client.force_login(self.owner)
        problem = make_problem(created_by=self.owner, content="Old statement")
        add_to_list(self.pl, problem)

        r = self.client.post(
            f"/lists/{self.pl.pk}/bulk-edit/save/",
            data='["not an object"]',
            content_type="application/json",
        )

        self.assertEqual(r.status_code, 400)
        problem.refresh_from_db()
        self.assertEqual(problem.content.get().source_for("en"), "Old statement")


class ProblemListItemUniqueTest(TestCase):
    def test_unique_problem_per_list(self):
        user = make_user(username="pli")
        pl = make_list(title="U", created_by=user)
        p = make_problem()
        ProblemListItem.objects.create(problem_list=pl, problem=p, order=1)
        with self.assertRaises(IntegrityError):
            ProblemListItem.objects.create(problem_list=pl, problem=p, order=2)
