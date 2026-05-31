from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from skoljka.apps.tracking.models import Submission
from skoljka.tests.factories import (
    make_problem,
    make_source,
    make_tag,
    make_user,
)


class SearchViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.src = make_source(slug="imo", name="IMO")
        cls.tag = make_tag(slug="algebra", name="Algebra")

        cls.p_fermat = make_problem(
            title="Fermat riddle",
            source=cls.src,
            year=2020,
            content="Prove that fermat's last theorem implies something delightful.",
        )
        cls.p_fermat.tags.add(cls.tag)

        cls.p_ramanujan = make_problem(
            title="Ramanujan partition",
            source=cls.src,
            year=2021,
            content="Ramanujan discovered partitions galore.",
        )

        cls.p_euler = make_problem(
            title="Graphs of Euler",
            year=2022,
            content="Study connected graphs via Euler's bridges.",
        )

    def test_full_text_finds_body_match(self):
        r = self.client.get("/search/?q=delightful")
        self.assertContains(r, self.p_fermat.title)
        self.assertNotContains(r, self.p_ramanujan.title)

    def test_multi_word_full_text_finds_body_match(self):
        r = self.client.get("/search/?q=last+theorem")
        self.assertContains(r, self.p_fermat.title)
        self.assertNotContains(r, self.p_ramanujan.title)

    def test_multi_word_title_fallback_requires_all_tokens(self):
        r = self.client.get("/search/?q=Euler+Graphs")
        self.assertContains(r, self.p_euler.title)
        self.assertNotContains(r, self.p_fermat.title)

    def test_title_substring_fallback(self):
        """Title substring match works even when FTS misses."""
        r = self.client.get("/search/?q=Ramanujan")
        self.assertContains(r, self.p_ramanujan.title)

    def test_source_filter(self):
        r = self.client.get(f"/search/?q=a&source={self.src.slug}")
        self.assertContains(r, self.p_fermat.title)
        self.assertNotContains(r, self.p_euler.title)

    def test_source_filter_includes_descendants(self):
        parent = make_source(slug="parent-contest", name="Parent Contest")
        child = make_source(slug="child-contest", name="Child Contest", parent=parent)
        child_problem = make_problem(title="Child source marker", source=child, content="descendant marker")

        r = self.client.get(f"/search/?q=descendant&source={parent.slug}")

        self.assertContains(r, child_problem.title)

    def test_year_filter(self):
        r = self.client.get("/search/?q=a&year=2022")
        self.assertContains(r, self.p_euler.title)
        self.assertNotContains(r, self.p_fermat.title)

    def test_tag_filter(self):
        r = self.client.get(f"/search/?q=a&tags={self.tag.slug}")
        self.assertContains(r, self.p_fermat.title)
        self.assertNotContains(r, self.p_euler.title)

    def test_nav_search_uses_tag_picker_state(self):
        r = self.client.get(f"/search/?q=fermat&tags={self.tag.slug}")
        self.assertContains(r, 'data-query-name="q"')
        self.assertContains(r, 'data-initial-query="fermat"')
        self.assertContains(r, f'&quot;{self.tag.slug}&quot;')
        self.assertContains(r, 'class="tag-pill"')

    def test_search_form_uses_merged_query_tag_picker(self):
        r = self.client.get("/search/")

        self.assertContains(r, 'data-query-name="q"')
        self.assertContains(r, 'type="search"')
        self.assertNotContains(r, 'id="search-q"')

    def test_source_dropdown_shows_hierarchy(self):
        parent = make_source(slug="dropdown-parent", name="Dropdown Parent")
        make_source(slug="dropdown-child", name="Dropdown Child", parent=parent)

        r = self.client.get("/search/")

        self.assertContains(r, ">Dropdown Parent</option>")
        self.assertContains(r, ">-- Dropdown Child</option>")

    def test_year_dropdown_deduplicates_years(self):
        make_problem(title="Another 2020", year=2020, content="year duplicate marker")

        r = self.client.get("/search/")
        html = r.content.decode()

        self.assertEqual(html.count('value="2020"'), 1)

    def test_multiple_tag_filters_are_and(self):
        other = make_tag(slug="number-theory", name="Number Theory")
        self.p_fermat.tags.add(other)
        self.p_euler.tags.add(self.tag)
        r = self.client.get(f"/search/?q=a&tags={self.tag.slug}&tags={other.slug}")
        self.assertContains(r, self.p_fermat.title)
        self.assertNotContains(r, self.p_euler.title)

    def test_combined_filters_and(self):
        r = self.client.get(f"/search/?q=a&source={self.src.slug}&year=2021")
        self.assertContains(r, self.p_ramanujan.title)
        self.assertNotContains(r, self.p_fermat.title)

    def test_status_solved_filter(self):
        user = make_user(username="solver-search")
        Submission.objects.create(user=user, problem=self.p_fermat, solved=True)
        self.client.force_login(user)
        r = self.client.get("/search/?q=a&status=solved")
        self.assertContains(r, self.p_fermat.title)
        self.assertNotContains(r, self.p_ramanujan.title)

    def test_status_unsolved_filter(self):
        user = make_user(username="unsolver-search")
        Submission.objects.create(user=user, problem=self.p_fermat, solved=True)
        self.client.force_login(user)
        r = self.client.get("/search/?q=a&status=unsolved")
        self.assertNotContains(r, self.p_fermat.title)
        self.assertContains(r, self.p_ramanujan.title)

    def test_anon_sees_only_public(self):
        alice = make_user(username="sa")
        private = make_problem(
            title="Secret",
            created_by=alice,
            is_public=False,
            content="SecretBody xyzzy",
        )
        r = self.client.get("/search/?q=xyzzy")
        self.assertNotContains(r, private.title)

    def test_private_not_visible_to_other_user(self):
        alice = make_user(username="sb1")
        bob = make_user(username="sb2")
        make_problem(
            title="PrivSecret",
            created_by=alice,
            is_public=False,
            content="Zingzang marker",
        )
        self.client.force_login(bob)
        r = self.client.get("/search/?q=Zingzang")
        self.assertNotContains(r, "PrivSecret")

    def test_problem_view_query_param_renders_cards(self):
        r = self.client.get("/search/?q=Fermat&view=cards")

        self.assertContains(r, "problem-view-actions")
        self.assertContains(r, "problem-card")
        self.assertContains(r, "Prove that fermat")

    def test_pdf_export_button_requires_login(self):
        r = self.client.get("/search/?q=Fermat")
        self.assertNotContains(r, "/search/pdf/?q=Fermat")

        self.client.force_login(make_user(username="search-pdf-user"))
        r = self.client.get("/search/?q=Fermat")
        self.assertContains(r, "/search/pdf/?q=Fermat")

    @patch("skoljka.apps.problems.export_views.export_problems_pdf")
    def test_pdf_export_uses_filtered_results(self, export_pdf):
        export_pdf.return_value = SimpleNamespace(filename="search-results.pdf", data=b"%PDF")
        self.client.force_login(make_user(username="search-pdf-user-2"))

        r = self.client.post("/search/pdf/?q=Fermat", {"title": "Search results", "heading_mode": "number", "action": "download"})

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        problems = export_pdf.call_args.args[0]
        self.assertEqual([p.pk for p in problems], [self.p_fermat.pk])

    @patch("skoljka.apps.problems.export_views.export_problems_latex_zip")
    def test_latex_export_uses_filtered_results(self, export_latex):
        export_latex.return_value = SimpleNamespace(filename="search-results.zip", data=b"zip")
        self.client.force_login(make_user(username="search-latex-user"))

        r = self.client.post("/search/pdf/?q=Fermat", {"title": "Search results", "heading_mode": "number", "action": "latex"})

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/zip")
        problems = export_latex.call_args.args[0]
        self.assertEqual([p.pk for p in problems], [self.p_fermat.pk])

    def test_problem_view_cookie_is_scoped(self):
        self.client.cookies["problem_views"] = "search:c,source-year:t,list:t,problems:t"

        r = self.client.get("/search/?q=Fermat")

        self.assertContains(r, "problem-card")
        self.assertContains(r, 'data-problem-view-key="search"')

    def test_paginated_results(self):
        for i in range(105):
            make_problem(
                title=f"LimTitle uniqueword{i}",
                content="limitcheck marker",
            )
        r = self.client.get("/search/?q=limitcheck")
        self.assertContains(r, "105 results")
        self.assertNotContains(r, "Showing 1-10 of 105")
        self.assertContains(r, "page=2")


class SearchNoQueryTest(TestCase):
    def test_empty_query_no_results_block(self):
        make_problem(content="something")
        r = self.client.get("/search/")
        self.assertEqual(r.status_code, 200)
        # Without filters, results table isn't rendered.
        self.assertNotContains(r, "results")
