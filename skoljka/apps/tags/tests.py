import json

from django.test import TestCase
from django.urls import reverse
from django.utils.translation import override

from skoljka.apps.tags.cache import tag_api_url
from skoljka.apps.tags.models import Tag
from skoljka.tests.factories import make_problem, make_source, make_staff, make_tag, make_user


class TagNameFallbackTest(TestCase):
    def test_returns_requested_language(self):
        t = make_tag(slug="al", name="X", translations={"en": "Algebra", "hr": "Algebra_HR"})
        self.assertEqual(t.name("hr"), "Algebra_HR")

    def test_falls_back_to_english(self):
        t = make_tag(slug="al2", translations={"en": "Algebra"})
        self.assertEqual(t.name("fr"), "Algebra")

    def test_falls_back_to_slug(self):
        t = make_tag(slug="weirdslug", translations={})
        self.assertEqual(t.name("en"), "weirdslug")

    def test_display_name_prefers_short_translation(self):
        t = make_tag(
            slug="functional-equations",
            translations={"en": "Functional equations", "hr": "Funkcijske jednadžbe"},
            short_translations={"en": "FE", "hr": "FJ"},
        )
        self.assertEqual(t.display_name("en"), "FE")
        self.assertEqual(t.display_name("hr"), "FJ")

    def test_display_name_uses_active_language_by_default(self):
        t = make_tag(
            slug="number-theory",
            translations={"en": "Number theory", "hr": "Teorija brojeva"},
            short_translations={"en": "NT", "hr": "TB"},
        )
        with override("hr"):
            self.assertEqual(t.display_name(), "TB")

    def test_display_name_falls_back_to_full_name(self):
        t = make_tag(slug="algebra", translations={"en": "Algebra"})
        self.assertEqual(t.display_name("en"), "Algebra")

    def test_parent_fk(self):
        parent = make_tag(slug="math", name="Math")
        child = make_tag(slug="algebra-sub", name="Algebra", parent=parent)
        self.assertIn(child, parent.children.all())

    def test_absolute_url_points_to_search_filter(self):
        tag = make_tag(slug="geometry", name="Geometry")
        self.assertEqual(tag.get_absolute_url(), "/search/?tags=geometry")


class TagPageRoutesRemovedTest(TestCase):
    def test_tag_list_route_removed(self):
        r = self.client.get("/tags/")
        self.assertEqual(r.status_code, 404)

    def test_tag_detail_route_removed(self):
        tag = make_tag(slug="algebra", name="Algebra")
        r = self.client.get(f"/tags/{tag.slug}/")
        self.assertEqual(r.status_code, 404)


class TagApiViewTest(TestCase):
    def test_returns_json_with_expected_shape(self):
        t = make_tag(slug="api1", name="ApiOne", short_translations={"en": "API"})
        r = self.client.get(tag_api_url("en"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["Cache-Control"], "public, max-age=31536000, immutable")
        data = json.loads(r.content)
        self.assertIn("names", data)
        self.assertIn("full_names", data)
        self.assertIn("slugs", data)
        self.assertIn("kinds", data)
        self.assertIn("API", data["names"])
        self.assertIn("ApiOne", data["full_names"])
        self.assertIn("api1", data["slugs"])

    def test_excludes_hidden(self):
        make_tag(slug="apivis", name="Vis")
        make_tag(slug="apihid", name="Hid", hidden=True)
        r = self.client.get(tag_api_url("en"))
        data = json.loads(r.content)
        self.assertIn("apivis", data["slugs"])
        self.assertNotIn("apihid", data["slugs"])


class TagAdminViewTest(TestCase):
    def test_non_staff_cannot_access_tag_admin(self):
        self.client.force_login(make_user())
        r = self.client.get(reverse("tag_admin_list"))
        self.assertEqual(r.status_code, 403)

    def test_staff_can_see_tag_admin_link_from_problem_admin(self):
        self.client.force_login(make_staff())
        r = self.client.get(reverse("problem_admin_list"))
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn(reverse("tag_admin_list"), html)
        self.assertIn("Manage Tags", html)

    def test_staff_can_see_tag_admin_link_from_problem_list(self):
        self.client.force_login(make_staff())
        r = self.client.get(reverse("problem_list"))
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn(reverse("tag_admin_list"), html)
        self.assertIn("Manage Tags", html)

    def test_staff_can_create_tag_with_translations_and_descriptions(self):
        self.client.force_login(make_staff())
        r = self.client.post(
            reverse("tag_admin_list"),
            {
                "action": "create",
                "slug": "functional-equations",
                "kind": Tag.Kind.TOPIC,
                "name_en": "Functional equations",
                "name_hr": "Funkcijske jednadžbe",
                "short_name_en": "FE",
                "short_name_hr": "FJ",
                "description_en": "Equations whose unknowns are functions.",
                "description_hr": "Jednadžbe u kojima su nepoznanice funkcije.",
            },
        )
        self.assertRedirects(r, reverse("tag_admin_list"))
        tag = Tag.objects.get(slug="functional-equations")
        self.assertEqual(tag.translations["hr"], "Funkcijske jednadžbe")
        self.assertEqual(tag.short_translations["en"], "FE")
        self.assertEqual(tag.descriptions["en"], "Equations whose unknowns are functions.")

    def test_staff_can_update_tag_translations_and_descriptions(self):
        self.client.force_login(make_staff())
        tag = make_tag(
            slug="ineq",
            translations={"en": "Inequality"},
            descriptions={"en": "Old"},
        )
        r = self.client.post(
            reverse("tag_admin_edit", kwargs={"pk": tag.pk}),
            {
                "slug": "inequality",
                "kind": Tag.Kind.TECHNIQUE,
                "parent": "",
                "hidden": "on",
                "name_en": "Inequalities",
                "name_hr": "Nejednakosti",
                "short_name_en": "Ineq",
                "short_name_hr": "Nej",
                "description_en": "Problems about inequalities.",
                "description_hr": "Zadaci o nejednakostima.",
            },
        )
        self.assertRedirects(r, reverse("tag_admin_list"))
        tag.refresh_from_db()
        self.assertEqual(tag.slug, "inequality")
        self.assertEqual(tag.kind, Tag.Kind.TECHNIQUE)
        self.assertTrue(tag.hidden)
        self.assertEqual(tag.translations["hr"], "Nejednakosti")
        self.assertEqual(tag.short_translations["hr"], "Nej")
        self.assertEqual(tag.descriptions["hr"], "Zadaci o nejednakostima.")

    def test_tag_admin_list_is_read_only_with_explicit_edit_link(self):
        self.client.force_login(make_staff())
        tag = make_tag(slug="algebra", translations={"en": "Algebra", "hr": "Algebra"})
        r = self.client.get(reverse("tag_admin_list"))
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn(reverse("tag_admin_edit", kwargs={"pk": tag.pk}), html)
        self.assertNotIn(f'tag_{tag.pk}_slug', html)

    def test_tag_admin_list_shows_related_counts_for_delete_context(self):
        self.client.force_login(make_staff())
        tag = make_tag(slug="geometry", name="Geometry")
        problem = make_problem(title="Problem")
        problem.tags.add(tag)
        source = make_source(slug="imo", name="IMO")
        source.tags.add(tag)
        make_tag(slug="triangles", parent=tag)

        r = self.client.get(reverse("tag_admin_list"))
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn("geometry", html)
        self.assertIn("1", html)
        self.assertIn("Delete tag", html)

    def test_staff_can_delete_unused_tag(self):
        self.client.force_login(make_staff())
        tag = make_tag(slug="unused", name="Unused")
        r = self.client.post(reverse("tag_admin_delete", kwargs={"pk": tag.pk}))
        self.assertRedirects(r, reverse("tag_admin_list"))
        self.assertFalse(Tag.objects.filter(pk=tag.pk).exists())

    def test_delete_refuses_tag_with_children(self):
        self.client.force_login(make_staff())
        parent = make_tag(slug="parent", name="Parent")
        child = make_tag(slug="child", name="Child", parent=parent)
        r = self.client.post(reverse("tag_admin_delete", kwargs={"pk": parent.pk}))
        self.assertRedirects(r, reverse("tag_admin_list"))
        self.assertTrue(Tag.objects.filter(pk=parent.pk).exists())
        self.assertTrue(Tag.objects.filter(pk=child.pk).exists())
