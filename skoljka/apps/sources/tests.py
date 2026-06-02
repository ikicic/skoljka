import json
import zipfile
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError

from django.test import TestCase, override_settings
from django.utils.translation import override

from skoljka.apps.content.models import ContentAttachment
from skoljka.apps.problems.models import Problem
from skoljka.apps.sources.archive_transfer import (
    ExportOptions,
    ImportOptions,
    apply_import,
    export_archive,
    plan_import,
)
from skoljka.apps.sources.models import Source, SourceDocument
from skoljka.apps.tracking.models import Submission
from skoljka.tests.factories import (
    make_problem,
    make_source,
    make_staff,
    make_tag,
    make_user,
)


class SourceModelTest(TestCase):
    def test_slug_uniqueness(self):
        make_source(slug="srcdup")
        with self.assertRaises(IntegrityError):
            make_source(slug="srcdup")

    def test_name_fallback_chain(self):
        s = make_source(slug="fall", translations={"hr": {"name": "HRName"}})
        self.assertEqual(s.name("hr"), "HRName")
        # Missing "en", falls back to slug.
        self.assertEqual(s.name("en"), "fall")
        # Missing requested language, but "en" also missing -> slug.
        self.assertEqual(s.name("fr"), "fall")

    def test_name_uses_active_language(self):
        s = make_source(
            slug="lang-source",
            translations={"en": {"name": "English Name"}, "hr": {"name": "Hrvatski naziv"}},
        )

        with override("hr"):
            self.assertEqual(s.name(), "Hrvatski naziv")

    def test_parent_fk_hierarchy(self):
        parent = make_source(slug="p1", name="Parent")
        child = make_source(slug="c1", name="Child", parent=parent)
        self.assertIn(child, parent.children.all())

    def test_source_document_upload_name_cannot_escape_document_directory(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            source = make_source(slug="doc-safe-source", name="Doc Safe Source")
            document = SourceDocument(source=source, original_filename="../unsafe/contest.pdf")
            document.file.save("../unsafe/contest.pdf", ContentFile(b"pdf"), save=True)

            self.assertTrue(document.file.name.startswith("documents/"))
            self.assertTrue(document.file.name.endswith("/contest.pdf"))
            self.assertNotIn("..", document.file.name)


class SourceListViewTest(TestCase):
    def test_shows_root_sources(self):
        make_source(slug="root1", name="Root One")
        r = self.client.get("/archive/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Root One")

    def test_counts_match_db(self):
        root = make_source(slug="rc", name="RC")
        make_problem(source=root, year=2020, problem_label="1")
        make_problem(source=root, year=2020, problem_label="2")
        r = self.client.get("/archive/")
        self.assertContains(r, "2020")
        self.assertContains(r, '<th class="col-progress">Problems</th>')
        self.assertContains(r, '<span class="progress-text">2</span>')
        self.assertNotContains(r, '<span class="solved-count">0</span>/2')
        self.assertNotContains(r, "favorite-toggle")

    def test_counts_include_authenticated_users_solved_problems(self):
        user = make_user(username="solver")
        root = make_source(slug="solved-counts", name="Solved Counts")
        p1 = make_problem(source=root, year=2020, problem_label="1")
        make_problem(source=root, year=2020, problem_label="2")
        Submission.objects.create(user=user, problem=p1, solved=True)

        self.client.force_login(user)
        r = self.client.get("/archive/")

        self.assertContains(r, '<span class="solved-count">1</span>/2')
        self.assertContains(r, f'hx-post="/tracking/sources/{root.pk}/favorite/"')

    def test_shows_year_progress_cells(self):
        user = make_user(username="year-progress")
        root = make_source(slug="year-progress", name="Year Progress")
        p1 = make_problem(source=root, year=2020, problem_label="1")
        make_problem(source=root, year=2020, problem_label="2")
        p3 = make_problem(source=root, year=2021, problem_label="1")
        Submission.objects.create(user=user, problem=p1, solved=True)
        Submission.objects.create(user=user, problem=p3, solved=True)

        self.client.force_login(user)
        r = self.client.get("/archive/")

        self.assertContains(r, '<th class="col-grid">Years</th>')
        self.assertContains(r, 'href="/archive/year-progress/2020/"')
        self.assertContains(r, 'title="2020: 2 problems"')
        self.assertContains(r, 'class="mini-grid-cell partial"')
        self.assertContains(r, 'href="/archive/year-progress/2021/"')
        self.assertContains(r, 'title="2021: 1 problem"')
        self.assertContains(r, 'class="mini-grid-cell solved"')

    def test_root_leaf_rows_are_grouped_as_other_competitions(self):
        make_source(slug="root-leaf-a", name="Root Leaf A")
        make_source(slug="root-leaf-b", name="Root Leaf B")

        r = self.client.get("/archive/")

        self.assertContains(r, "Other competitions")
        self.assertContains(r, 'class="source-child-row"', count=2)

    def test_parent_with_children_and_own_problems_has_own_row(self):
        parent = make_source(slug="parent-own", name="Parent Own")
        child = make_source(slug="parent-child", name="Parent Child", parent=parent)
        make_problem(source=parent, year=2024, problem_label="1")
        make_problem(source=child, year=2024, problem_label="1")

        r = self.client.get("/archive/")
        html = r.content.decode()

        self.assertContains(r, f'<tr class="category-row"><td colspan="5"><a href="/archive/{parent.slug}/">Parent Own</a></td></tr>')
        self.assertContains(r, 'class="source-own-row"')
        self.assertContains(r, 'class="source-child-row"')
        self.assertLess(html.index('class="source-own-row"'), html.index('Parent Child'))

    def test_shows_nested_source_hierarchy(self):
        root = make_source(slug="cro", name="Croatian Competitions")
        contest = make_source(slug="cro-national", name="Croatian National Competition", parent=root)
        grade = make_source(slug="cro-grade-9", name="Grade 9", parent=contest)
        make_problem(source=grade, year=2024, problem_label="1")

        r = self.client.get("/archive/")
        html = r.content.decode()

        self.assertContains(r, "Croatian Competitions")
        self.assertContains(r, "Croatian National Competition")
        self.assertContains(r, "Grade 9")
        self.assertLess(html.index("Croatian Competitions"), html.index("Croatian National Competition"))
        self.assertLess(html.index("Croatian National Competition"), html.index("Grade 9"))

    def test_category_rows_link_to_source_page(self):
        root = make_source(slug="category-link-root", name="Category Link Root")
        make_source(slug="category-link-child", name="Category Link Child", parent=root)

        r = self.client.get("/archive/")

        self.assertContains(r, f'href="/archive/{root.slug}/"')
        self.assertNotContains(r, f'href="/archive/manage/{root.pk}/edit/"')

    def test_for_user_filter(self):
        alice = make_user(username="saw")
        make_source(slug="hiddensrc", name="HiddenName", created_by=alice, is_public=False)
        r = self.client.get("/archive/")
        self.assertNotContains(r, "HiddenName")

    def test_staff_sees_archive_edit_action(self):
        staff = make_staff(username="archive-staff")
        self.client.force_login(staff)
        r = self.client.get("/archive/")
        self.assertContains(r, 'href="/archive/manage/"')
        self.assertContains(r, ">Edit</a>")
        self.assertNotContains(r, 'href="/archive/manage/export/"')

    def test_regular_user_does_not_see_archive_edit_action(self):
        user = make_user(username="archive-user")
        self.client.force_login(user)
        r = self.client.get("/archive/")
        self.assertNotContains(r, 'href="/archive/manage/"')
        self.assertNotContains(r, 'href="/archive/manage/export/"')


class SourceDetailViewTest(TestCase):
    def test_public_visible_and_contains_sub_sources(self):
        root = make_source(slug="dr", name="Root")
        make_source(slug="dc", name="ChildSource", parent=root)
        r = self.client.get(f"/archive/{root.slug}/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "ChildSource")
        self.assertContains(r, "<th>Competition</th>")
        self.assertContains(r, 'class="source-child-row"')

    def test_source_detail_child_table_shows_child_year_stats(self):
        root = make_source(slug="child-table-root", name="Child Table Root")
        child = make_source(slug="child-table-child", name="Child Table Child", parent=root)
        make_problem(source=child, year=2022, problem_label="1")
        make_problem(source=child, year=2024, problem_label="1")

        r = self.client.get(f"/archive/{root.slug}/")

        self.assertContains(r, "Child Table Child")
        self.assertContains(r, "2022–2024")
        self.assertContains(r, 'href="/archive/child-table-child/2022/"')
        self.assertContains(r, 'href="/archive/child-table-child/2024/"')

    def test_year_grid_places_problems(self):
        src = make_source(slug="grd", name="Grid")
        p1 = make_problem(source=src, year=2024, problem_label="1", title="Prob1")
        make_problem(source=src, year=2024, problem_label="2", title="Prob2")
        r = self.client.get(f"/archive/{src.slug}/")
        self.assertContains(r, "2024")
        self.assertContains(r, "comp-grid")
        self.assertContains(r, f'/archive/{src.slug}/2024/')
        self.assertContains(r, f'<tr class="comp-grid-row" data-row-href="/archive/{src.slug}/2024/">')
        self.assertContains(r, f'href="{p1.get_absolute_url()}"')

    def test_year_grid_marks_authenticated_users_solved_problems(self):
        user = make_user(username="grid-solver")
        src = make_source(slug="grid-solved", name="Grid Solved")
        p1 = make_problem(source=src, year=2024, problem_label="1", title="Solved")
        make_problem(source=src, year=2024, problem_label="2", title="Unsolved")
        make_problem(source=src, year=2024, problem_label="3", title="Unsolved Too")
        Submission.objects.create(user=user, problem=p1, solved=True)

        self.client.force_login(user)
        r = self.client.get(f"/archive/{src.slug}/")

        self.assertContains(r, '<td class="cell solved"><a href=')
        self.assertContains(r, '<td class="year-summary">1/3</td>')

    def test_year_grid_renders_missing_problem_labels_as_empty_cells(self):
        src = make_source(slug="sparse-grid", name="Sparse Grid")
        make_problem(source=src, year=2024, problem_label="1")
        make_problem(source=src, year=2024, problem_label="2")
        make_problem(source=src, year=2023, problem_label="1")

        r = self.client.get(f"/archive/{src.slug}/")

        self.assertContains(r, '<td class="cell empty"></td>')

    def test_detail_shows_all_problems_table_sorted_by_year_desc(self):
        src = make_source(slug="all-problems", name="All Problems")
        make_problem(source=src, year=2023, problem_label="1", title="Older")
        make_problem(source=src, year=2024, problem_label="2", title="Second")
        make_problem(source=src, year=2024, problem_label="1", title="First")

        r = self.client.get(f"/archive/{src.slug}/")
        html = r.content.decode()

        self.assertContains(r, "<h2>Overview</h2>")
        self.assertContains(r, "<h2>Problems</h2>")
        self.assertContains(r, '<section class="problem-year-section">', count=2)
        self.assertContains(r, f'<h3><a href="/archive/{src.slug}/2024/">2024</a></h3>')
        self.assertContains(r, f'<h3><a href="/archive/{src.slug}/2023/">2023</a></h3>')
        self.assertLess(html.index("First"), html.index("Second"))
        self.assertLess(html.index("Second"), html.index("Older"))

    def test_year_query_shows_problem_cards_for_year(self):
        src = make_source(slug="yearfilter", name="Year Filter")
        make_problem(source=src, year=2024, problem_label="1", title="Visible", content="Full **statement**.")
        make_problem(source=src, year=2023, problem_label="1", title="Hidden")
        r = self.client.get(f"/archive/{src.slug}/2024/")
        self.assertContains(r, "<h1>Year Filter 2024</h1>")
        self.assertNotContains(r, "Problems 2024")
        self.assertContains(r, f'<a href="/archive/{src.slug}/">Year Filter</a>')
        self.assertContains(r, "problem-card")
        self.assertContains(r, "Visible")
        self.assertContains(r, "<strong>statement</strong>")
        self.assertNotContains(r, "Hidden")
        self.assertNotContains(r, "comp-grid")

    def test_year_query_shortens_all_generated_problem_titles(self):
        src = make_source(slug="yeargenerated", name="Generated Year")
        make_problem(source=src, year=2024, problem_label="1", content="First.")
        make_problem(source=src, year=2024, problem_label="2", content="Second.")

        r = self.client.get(f"/archive/{src.slug}/2024/")

        self.assertContains(r, 'class="problem-card-title">Problem 1</a>')
        self.assertContains(r, 'class="problem-card-title">Problem 2</a>')
        self.assertNotContains(r, "Generated Year 2024 Problem 1")

    def test_year_query_keeps_generated_problem_titles_if_any_title_is_custom(self):
        src = make_source(slug="yearmixedtitles", name="Mixed Year")
        make_problem(source=src, year=2024, problem_label="1", content="First.")
        make_problem(source=src, year=2024, problem_label="2", title="Custom", content="Second.")

        r = self.client.get(f"/archive/{src.slug}/2024/")

        self.assertContains(r, "Mixed Year 2024 Problem 1")
        self.assertContains(r, "Custom")

    def test_year_query_includes_descendant_source_problems(self):
        parent = make_source(slug="year-parent", name="Year Parent")
        child = make_source(slug="year-child", name="Year Child", parent=parent)
        grandchild = make_source(slug="year-grandchild", name="Year Grandchild", parent=child)
        make_problem(source=grandchild, year=2024, problem_label="1", content="Grandchild statement.")

        r = self.client.get(f"/archive/{parent.slug}/2024/")

        self.assertContains(r, "Grandchild statement.")
        self.assertNotContains(r, "No problems for this year.")
        self.assertContains(r, "Year Grandchild 2024 Problem 1")
        self.assertNotContains(r, 'class="problem-card-title">Problem 1</a>')

    def test_year_query_can_render_problem_table_from_cookie(self):
        src = make_source(slug="yearviewcookie", name="Year View Cookie")
        make_problem(source=src, year=2024, problem_label="1", title="Visible", content="Full statement.")
        self.client.cookies["problem_views"] = "search:c,source-year:t,list:t,problems:t"

        r = self.client.get(f"/archive/{src.slug}/2024/")

        self.assertContains(r, "table-wrapper")
        self.assertNotContains(r, "problem-card")
        self.assertContains(r, 'data-problem-view-key="source-year"')

    def test_year_query_paginates_problems(self):
        src = make_source(slug="year-paged", name="Year Paged")
        for i in range(55):
            make_problem(
                source=src,
                year=2024,
                problem_label=f"{i + 1:03d}",
                title=f"Paged {i:02d}",
            )

        r = self.client.get(f"/archive/{src.slug}/2024/")

        self.assertContains(r, "Paged 00")
        self.assertNotContains(r, "Paged 50")
        self.assertContains(r, "page=2")
        self.assertContains(r, "Showing 1-50 of 55")

        r = self.client.get(f"/archive/{src.slug}/2024/?page=2")

        self.assertNotContains(r, "Paged 00")
        self.assertContains(r, "Paged 50")
        self.assertContains(r, "Showing 51-55 of 55")

    def test_source_detail_paginates_problem_sections(self):
        src = make_source(slug="source-paged", name="Source Paged")
        for i in range(55):
            make_problem(
                source=src,
                year=2024,
                problem_label=f"{i + 1:03d}",
                title=f"Source Paged {i:02d}",
                content=f"Overview body {i:02d}",
            )

        r = self.client.get(f"/archive/{src.slug}/?view=cards")

        self.assertContains(r, "Overview body 00")
        self.assertNotContains(r, "Overview body 50")
        self.assertContains(r, "page=2")
        self.assertContains(r, "Showing 1-50 of 55")

        r = self.client.get(f"/archive/{src.slug}/?view=cards&page=2")

        self.assertNotContains(r, "Overview body 00")
        self.assertContains(r, "Overview body 50")
        self.assertContains(r, "Showing 51-55 of 55")

    def test_year_pdf_export_button_requires_login(self):
        src = make_source(slug="yearpdfbutton", name="Year PDF Button")
        make_problem(source=src, year=2024, problem_label="1", content="Full statement.")

        r = self.client.get(f"/archive/{src.slug}/2024/")
        self.assertNotContains(r, f"/archive/{src.slug}/2024/pdf/")

        self.client.force_login(make_user(username="year-pdf-user"))
        r = self.client.get(f"/archive/{src.slug}/2024/")
        self.assertContains(r, f"/archive/{src.slug}/2024/pdf/")

    @patch("skoljka.apps.problems.export_views.export_problems_pdf")
    def test_year_pdf_export_uses_visible_year_problems(self, export_pdf):
        export_pdf.return_value = SimpleNamespace(filename="year.pdf", data=b"%PDF")
        user = make_user(username="source-pdf-user")
        other = make_user(username="source-pdf-other")
        src = make_source(slug="yearpdf", name="Year PDF")
        first = make_problem(source=src, year=2024, problem_label="1", is_public=True)
        make_problem(source=src, year=2024, problem_label="2", is_public=False, created_by=other)

        self.client.force_login(user)
        r = self.client.post(f"/archive/{src.slug}/2024/pdf/", {"title": "Year PDF 2024", "heading_mode": "number", "action": "download"})

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        problems = export_pdf.call_args.args[0]
        self.assertEqual([p.pk for p in problems], [first.pk])
        self.assertEqual(export_pdf.call_args.kwargs["compact_generated_titles_for"], (src.pk, 2024))

    @patch("skoljka.apps.problems.export_views.export_problems_pdf")
    def test_year_pdf_export_includes_descendant_source_problems(self, export_pdf):
        export_pdf.return_value = SimpleNamespace(filename="year.pdf", data=b"%PDF")
        user = make_user(username="source-pdf-desc-user")
        parent = make_source(slug="yearpdf-parent", name="Year PDF Parent")
        child = make_source(slug="yearpdf-child", name="Year PDF Child", parent=parent)
        first = make_problem(source=parent, year=2024, problem_label="1", is_public=True)
        second = make_problem(source=child, year=2024, problem_label="1", is_public=True)

        self.client.force_login(user)
        r = self.client.post(f"/archive/{parent.slug}/2024/pdf/", {"title": "Year PDF Parent 2024", "heading_mode": "number", "action": "download"})

        self.assertEqual(r.status_code, 200)
        problems = export_pdf.call_args.args[0]
        self.assertEqual([p.pk for p in problems], [first.pk, second.pk])
        self.assertIsNone(export_pdf.call_args.kwargs["compact_generated_titles_for"])

    @patch("skoljka.apps.problems.export_views.export_problems_pdf")
    def test_source_pdf_export_matches_archive_page_problem_scope(self, export_pdf):
        export_pdf.return_value = SimpleNamespace(filename="source.pdf", data=b"%PDF")
        user = make_user(username="source-pdf-page-scope-user")
        parent = make_source(slug="sourcepdf-parent", name="Source PDF Parent")
        child = make_source(slug="sourcepdf-child", name="Source PDF Child", parent=parent)
        first = make_problem(source=parent, year=2024, problem_label="1", is_public=True)
        second = make_problem(source=child, year=2023, problem_label="1", is_public=True)

        self.client.force_login(user)
        r = self.client.post(f"/archive/{parent.slug}/pdf/", {"title": parent.name(), "heading_mode": "number", "action": "download"})

        self.assertEqual(r.status_code, 200)
        problems = export_pdf.call_args.args[0]
        self.assertEqual([p.pk for p in problems], [first.pk, second.pk])

    def test_year_query_shows_bulk_edit_action_for_staff(self):
        user = make_staff(username="source-bulk-editor")
        src = make_source(slug="source-bulk-action", name="Source Bulk Action")
        make_problem(source=src, year=2024, problem_label="1", created_by=user)

        self.client.force_login(user)
        r = self.client.get(f"/archive/{src.slug}/2024/")

        self.assertContains(r, f'href="/archive/{src.slug}/2024/bulk-edit/"')
        self.assertContains(r, ">Bulk edit</a>")

    def test_year_query_shows_bulk_delete_form_for_staff(self):
        staff = make_staff(username="source-bulk-delete-form")
        src = make_source(slug="source-bulk-delete-form", name="Source Bulk Delete Form")
        make_problem(source=src, year=2024, problem_label="1")
        make_problem(source=src, year=2024, problem_label="2")

        self.client.force_login(staff)
        r = self.client.get(f"/archive/{src.slug}/2024/")

        self.assertContains(r, f'action="/archive/{src.slug}/2024/delete-problems/"')
        self.assertContains(r, 'data-confirm-count-form=""')
        self.assertContains(r, 'data-confirm-count-expected=""')
        self.assertContains(r, 'data-confirm-count-input=""')
        self.assertContains(r, 'name="confirm_count"')
        self.assertContains(r, '<button type="submit" class="btn btn-sm btn-danger" disabled>')

    def test_year_bulk_delete_requires_staff(self):
        user = make_user(username="source-bulk-delete-user")
        src = make_source(slug="source-bulk-delete-staff", name="Source Bulk Delete Staff")
        make_problem(source=src, year=2024, problem_label="1")

        self.client.force_login(user)
        r = self.client.post(
            f"/archive/{src.slug}/2024/delete-problems/",
            {"expected_count": "1", "confirm_count": "1"},
        )

        self.assertEqual(r.status_code, 403)
        self.assertEqual(Problem.objects.count(), 1)

    def test_year_bulk_delete_requires_matching_count(self):
        staff = make_staff(username="source-bulk-delete-count")
        src = make_source(slug="source-bulk-delete-count", name="Source Bulk Delete Count")
        make_problem(source=src, year=2024, problem_label="1")
        make_problem(source=src, year=2024, problem_label="2")

        self.client.force_login(staff)
        r = self.client.post(
            f"/archive/{src.slug}/2024/delete-problems/",
            {"expected_count": "2", "confirm_count": "1"},
        )

        self.assertEqual(r.status_code, 400)
        self.assertEqual(Problem.objects.count(), 2)

    def test_year_bulk_delete_deletes_visible_year_descendant_problems(self):
        staff = make_staff(username="source-bulk-delete-ok")
        parent = make_source(slug="source-bulk-delete-parent", name="Source Bulk Delete Parent")
        child = make_source(slug="source-bulk-delete-child", name="Source Bulk Delete Child", parent=parent)
        direct = make_problem(source=parent, year=2024, problem_label="1")
        descendant = make_problem(source=child, year=2024, problem_label="1")
        other_year = make_problem(source=child, year=2023, problem_label="1")

        self.client.force_login(staff)
        r = self.client.post(
            f"/archive/{parent.slug}/2024/delete-problems/",
            {"expected_count": "2", "confirm_count": "2"},
        )

        self.assertRedirects(r, f"/archive/{parent.slug}/2024/")
        self.assertFalse(Problem.objects.filter(pk__in=[direct.pk, descendant.pk]).exists())
        self.assertTrue(Problem.objects.filter(pk=other_year.pk).exists())

    def test_source_bulk_delete_deletes_all_visible_descendant_problems(self):
        staff = make_staff(username="source-bulk-delete-all")
        parent = make_source(slug="source-bulk-delete-all-parent", name="Source Bulk Delete All Parent")
        child = make_source(slug="source-bulk-delete-all-child", name="Source Bulk Delete All Child", parent=parent)
        direct = make_problem(source=parent, year=2024, problem_label="1")
        descendant = make_problem(source=child, year=2023, problem_label="1")

        self.client.force_login(staff)
        r = self.client.post(
            f"/archive/{parent.slug}/delete-problems/",
            {"expected_count": "2", "confirm_count": "2"},
        )

        self.assertRedirects(r, f"/archive/{parent.slug}/")
        self.assertFalse(Problem.objects.filter(pk__in=[direct.pk, descendant.pk]).exists())

    def test_source_year_bulk_edit_renders_context(self):
        user = make_staff(username="source-bulk-render")
        src = make_source(slug="source-bulk-render", name="Source Bulk Render")
        make_problem(source=src, year=2024, problem_label="1", created_by=user, content="Editable statement")

        self.client.force_login(user)
        r = self.client.get(f"/archive/{src.slug}/2024/bulk-edit/")

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'id="list-bulk-edit"')
        self.assertContains(r, "Source Bulk Render 2024")
        self.assertContains(r, "Editable statement")
        self.assertContains(r, f'data-save-url="/archive/{src.slug}/2024/bulk-edit/save/"')

    def test_source_year_bulk_edit_with_document_renders_pdf_payload(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            user = make_staff(username="source-bulk-pdf-render")
            src = make_source(slug="source-bulk-pdf-render", name="Source Bulk PDF Render")
            make_problem(source=src, year=2024, problem_label="1", created_by=user, content="Editable statement")
            document = SourceDocument(
                source=src,
                year=2024,
                language="hr",
                kind=SourceDocument.Kind.PROBLEMS,
                original_filename="visual.pdf",
            )
            document.file.save("visual.pdf", ContentFile(b"pdf"), save=True)

            self.client.force_login(user)
            r = self.client.get(f"/archive/{src.slug}/2024/bulk-edit/?document={document.pk}")

            self.assertEqual(r.status_code, 200)
            self.assertContains(r, '"document":')
            self.assertContains(r, "visual.pdf")
            self.assertContains(r, "/media/documents/")

    def test_source_year_bulk_edit_requires_staff(self):
        user = make_user(username="source-bulk-nonstaff")
        src = make_source(slug="source-bulk-nonstaff", name="Source Bulk Nonstaff")
        make_problem(source=src, year=2024, problem_label="1", created_by=user, content="Editable statement")

        self.client.force_login(user)
        r = self.client.get(f"/archive/{src.slug}/2024/bulk-edit/")

        self.assertEqual(r.status_code, 403)

    def test_source_year_bulk_edit_save_updates_content(self):
        user = make_staff(username="source-bulk-save")
        src = make_source(slug="source-bulk-save", name="Source Bulk Save")
        problem = make_problem(source=src, year=2024, problem_label="1", created_by=user, content="Old statement")

        self.client.force_login(user)
        r = self.client.post(
            f"/archive/{src.slug}/2024/bulk-edit/save/",
            data='{"problems":[{"id":%d,"source_md":"New statement","language":"en","tags":[],"new_tags":[]}]}' % problem.pk,
            content_type="application/json",
        )

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["redirect_url"], f"/archive/{src.slug}/2024/")
        problem.refresh_from_db()
        self.assertEqual(problem.content.get().source_for("en"), "New statement")

    def test_year_query_shows_source_documents(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            src = make_source(slug="docs-source", name="Docs Source")
            document = SourceDocument(
                source=src,
                year=2024,
                language="hr",
                kind=SourceDocument.Kind.PROBLEMS,
                original_filename="docs.pdf",
            )
            document.file.save("docs.pdf", ContentFile(b"pdf"), save=True)

            r = self.client.get(f"/archive/{src.slug}/2024/")

            self.assertContains(r, "Documents")
            self.assertContains(r, "<th>Year</th>")
            self.assertContains(r, "<th>Filename</th>")
            self.assertContains(r, "<th>Language</th>")
            self.assertContains(r, "docs.pdf")
            self.assertContains(r, "<td>2024</td>")
            self.assertContains(r, "<td>hr</td>")
            self.assertContains(r, "/media/documents/")

    def test_year_query_shows_document_bulk_edit_action_for_staff(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            staff = make_staff(username="source-document-bulk-edit")
            src = make_source(slug="docs-bulk-edit-source", name="Docs Bulk Edit Source")
            document = SourceDocument(
                source=src,
                year=2024,
                language="hr",
                kind=SourceDocument.Kind.PROBLEMS,
                original_filename="docs.pdf",
            )
            document.file.save("docs.pdf", ContentFile(b"pdf"), save=True)
            self.client.force_login(staff)

            r = self.client.get(f"/archive/{src.slug}/2024/")

            self.assertContains(r, f'href="/archive/{src.slug}/2024/bulk-edit/?document={document.pk}"')
            self.assertContains(r, "Bulk edit with this PDF")
            self.assertContains(r, "Use this PDF as a visual aid")

    def test_staff_can_delete_source_document(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            staff = make_staff(username="source-document-delete")
            src = make_source(slug="delete-doc-source", name="Delete Doc Source")
            document = SourceDocument(
                source=src,
                year=2024,
                language="hr",
                kind=SourceDocument.Kind.PROBLEMS,
                original_filename="delete-me.pdf",
            )
            document.file.save("delete-me.pdf", ContentFile(b"pdf"), save=True)
            file_path = document.file.path
            self.client.force_login(staff)

            r = self.client.get(f"/archive/{src.slug}/2024/")
            self.assertContains(r, f'action="/archive/documents/{document.pk}/delete/"')
            self.assertContains(r, ">Delete</button>")

            r = self.client.post(
                f"/archive/documents/{document.pk}/delete/",
                {"next": f"/archive/{src.slug}/2024/"},
            )

            self.assertRedirects(r, f"/archive/{src.slug}/2024/")
            self.assertFalse(SourceDocument.objects.filter(pk=document.pk).exists())
            self.assertFalse(Path(file_path).exists())

    def test_document_delete_requires_staff(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            user = make_user(username="source-document-delete-user")
            src = make_source(slug="delete-doc-forbidden", name="Delete Doc Forbidden")
            document = SourceDocument(source=src, original_filename="keep.pdf")
            document.file.save("keep.pdf", ContentFile(b"pdf"), save=True)
            self.client.force_login(user)

            r = self.client.post(f"/archive/documents/{document.pk}/delete/")

            self.assertEqual(r.status_code, 403)
            self.assertTrue(SourceDocument.objects.filter(pk=document.pk).exists())

    def test_source_detail_shows_all_source_documents(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            src = make_source(slug="all-docs-source", name="All Docs Source")
            for year, filename in (
                (2024, "z-docs-2024.pdf"),
                (None, "docs-general.pdf"),
                (2024, "a-docs-2024.pdf"),
                (2023, "docs-2023.pdf"),
            ):
                document = SourceDocument(
                    source=src,
                    year=year,
                    language="hr",
                    kind=SourceDocument.Kind.PROBLEMS,
                    original_filename=filename,
                )
                document.file.save(filename, ContentFile(b"pdf"), save=True)

            r = self.client.get(f"/archive/{src.slug}/")

            self.assertContains(r, "Documents")
            self.assertContains(r, "z-docs-2024.pdf")
            self.assertContains(r, "a-docs-2024.pdf")
            self.assertContains(r, "docs-2023.pdf")
            self.assertContains(r, "docs-general.pdf")
            self.assertContains(r, '<span class="text-muted">—</span>')
            html = r.content.decode()
            self.assertLess(html.index("a-docs-2024.pdf"), html.index("z-docs-2024.pdf"))
            self.assertLess(html.index("z-docs-2024.pdf"), html.index("docs-2023.pdf"))
            self.assertLess(html.index("docs-2023.pdf"), html.index("docs-general.pdf"))

    def test_source_problem_table_uses_source_view_cookie_key(self):
        src = make_source(slug="sourceviewcookie", name="Source View Cookie")
        make_problem(source=src, year=2024, problem_label="1", title="Visible", content="Full statement.")
        self.client.cookies["problem_views"] = "source:c,source-year:t"

        r = self.client.get(f"/archive/{src.slug}/")

        self.assertContains(r, "problem-card")
        self.assertContains(r, 'data-problem-view-key="source"')

    def test_unknown_slug_404(self):
        r = self.client.get("/archive/ghost/")
        self.assertEqual(r.status_code, 404)

    def test_staff_sees_source_export_action(self):
        staff = make_staff(username="source-export-staff")
        src = make_source(slug="source-export-action", name="Source Export Action")
        self.client.force_login(staff)

        r = self.client.get(f"/archive/{src.slug}/")

        self.assertContains(r, f'href="/archive/manage/{src.pk}/edit/"')
        self.assertContains(r, ">Edit</a>")
        self.assertContains(r, f'href="/archive/manage/export/?source={src.slug}"')
        self.assertContains(r, ">Export</a>")


class SourceExportViewTest(TestCase):
    def test_requires_staff(self):
        user = make_user(username="export-user")
        self.client.force_login(user)

        r = self.client.get("/archive/manage/export/")

        self.assertEqual(r.status_code, 403)

    def test_get_preselects_source(self):
        staff = make_staff(username="export-staff")
        src = make_source(slug="export-src", name="Export Source")
        self.client.force_login(staff)

        r = self.client.get(f"/archive/manage/export/?source={src.slug}")

        self.assertContains(r, "Export archive")
        self.assertContains(r, f'<option value="{src.slug}" selected')

    def test_post_downloads_zip(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            staff = make_staff(username="export-download-staff")
            src = make_source(slug="download-src", name="Download Source")
            make_problem(source=src, year=2024, problem_label="1", content="Exported statement")
            self.client.force_login(staff)

            r = self.client.post(
                "/archive/manage/export/",
                {
                    "sources": [src.slug],
                    "include_children": "on",
                    "include_documents": "on",
                    "include_attachments": "on",
                },
            )

            self.assertEqual(r.status_code, 200)
            self.assertEqual(r["Content-Type"], "application/zip")
            self.assertIn("skoljka-download-src.zip", r["Content-Disposition"])
            data = b"".join(r.streaming_content)
            zip_path = f"{tmp}/download.zip"
            with open(zip_path, "wb") as f:
                f.write(data)
            with zipfile.ZipFile(zip_path) as zf:
                sources = json.loads(zf.read("sources.json"))
                self.assertEqual(sources[0]["slug"], src.slug)


class ArchiveTransferTest(TestCase):
    def _write_archive(self, path, *, sources=None, tags=None, problems=None, documents=None, files=None):
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("manifest.json", json.dumps({"schema": "skoljka.archive.v1"}))
            zf.writestr("sources.json", json.dumps(sources or []))
            zf.writestr("tags.json", json.dumps(tags or []))
            zf.writestr("problems.json", json.dumps(problems or []))
            zf.writestr("source_documents.json", json.dumps(documents or []))
            for file_path, data in (files or {}).items():
                zf.writestr(file_path, data)

    def _problem_payload(self, *, source="imo", year=2024, number=1, text="Statement", tags=None, attachments=None):
        return {
            "key": f"{source}-{year}-{number}",
            "source": source,
            "year": year,
            "problem_label": number,
            "title": "",
            "is_public": True,
            "tags": tags or [],
            "content": {
                "original_language": "en",
                "source_md": {"en": text},
                "attachments": attachments or [],
            },
        }

    def test_export_archive_writes_json_and_files(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            source = make_source(slug="imo-export", name="IMO Export")
            tag = make_tag(slug="geometry", name="Geometry")
            problem = make_problem(source=source, year=2024, problem_label="2", content="Exported")
            problem.tags.add(tag)
            content = problem.content.get()
            ContentAttachment.from_upload(content, SimpleUploadedFile("figure.png", b"png", content_type="image/png"))
            document = SourceDocument(source=source, year=2024, kind=SourceDocument.Kind.PROBLEMS, original_filename="imo.pdf")
            document.file.save("imo.pdf", ContentFile(b"pdf"), save=True)

            output = f"{tmp}/archive.zip"
            summary = export_archive(ExportOptions(source_slugs=[source.slug], output=output))

            self.assertEqual(summary["sources"], 1)
            self.assertEqual(summary["problems"], 1)
            with zipfile.ZipFile(output) as zf:
                self.assertEqual(json.loads(zf.read("manifest.json"))["schema"], "skoljka.archive.v1")
                problems = json.loads(zf.read("problems.json"))
                self.assertEqual(problems[0]["source"], "imo-export")
                self.assertIn("files/content_attachments/imo-export/2024/2/figure.png", zf.namelist())
                self.assertIn("files/source_documents/imo-export/2024/problems/imo.pdf", zf.namelist())

    def test_import_creates_missing_records_and_is_idempotent(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            owner = make_staff(username="archive-owner")
            archive = f"{tmp}/import.zip"
            archive_file = "files/content_attachments/imo/2024/1/figure.png"
            self._write_archive(
                archive,
                sources=[{
                    "key": "imo",
                    "slug": "imo",
                    "parent": None,
                    "order": 5,
                    "is_public": True,
                    "translations": {"en": {"name": "IMO"}},
                    "tags": ["geometry"],
                }],
                tags=[{"slug": "geometry", "kind": "topic", "hidden": False, "translations": {"en": "Geometry"}}],
                problems=[self._problem_payload(
                    text="Statement\n\n![figure](attachment:figure.png)",
                    tags=["geometry"],
                    attachments=[{
                        "name": "figure.png",
                        "path": archive_file,
                        "content_type": "image/png",
                        "size": 3,
                        "sha256": __import__("hashlib").sha256(b"png").hexdigest(),
                    }],
                )],
                files={archive_file: b"png"},
            )

            options = ImportOptions(owner=owner, do_it=True)
            plan = plan_import(archive, options)
            self.assertTrue(plan.can_apply)
            apply_import(archive, options, plan)

            source = Source.objects.get(slug="imo")
            problem = Problem.objects.get(source=source, year=2024, problem_label="1")
            content = problem.content.get()
            self.assertEqual(source.created_by, owner)
            self.assertEqual(problem.created_by, owner)
            self.assertIn("Statement", content.source_for("en"))
            self.assertIn('src="/media/content/', content.html_for("en"))
            self.assertNotIn("attachment:figure.png", content.html_for("en"))
            self.assertEqual(set(problem.tags.values_list("slug", flat=True)), {"geometry"})

            second_plan = plan_import(archive, ImportOptions(owner=owner))
            self.assertTrue(second_plan.can_apply)
            self.assertEqual(second_plan.summary()["skip"]["problem"], 1)

    def test_existing_problem_difference_requires_policy(self):
        with TemporaryDirectory() as tmp:
            owner = make_staff(username="archive-owner-2")
            source = make_source(slug="imo", name="IMO")
            make_problem(source=source, year=2024, problem_label="1", content="Edited on target")
            archive = f"{tmp}/import.zip"
            self._write_archive(
                archive,
                sources=[{"key": "imo", "slug": "imo", "parent": None, "order": 0, "is_public": True, "translations": {"en": {"name": "IMO"}}, "tags": []}],
                problems=[self._problem_payload(text="Incoming")],
            )

            plan = plan_import(archive, ImportOptions(owner=owner))

            self.assertFalse(plan.can_apply)
            self.assertEqual(plan.unaddressed_conflicts, 1)
            self.assertEqual(plan.conflicts[0].object_type, "problem")

            skip_plan = plan_import(archive, ImportOptions(owner=owner, existing_problems="skip"))
            self.assertTrue(skip_plan.can_apply)
            apply_import(archive, ImportOptions(owner=owner, existing_problems="skip", do_it=True), skip_plan)
            self.assertEqual(Problem.objects.get(source=source, year=2024, problem_label="1").content.get().source_for("en"), "Edited on target")

            overwrite_options = ImportOptions(owner=owner, existing_problems="overwrite", do_it=True)
            overwrite_plan = plan_import(archive, overwrite_options)
            self.assertTrue(overwrite_plan.can_apply)
            apply_import(archive, overwrite_options, overwrite_plan)
            self.assertEqual(Problem.objects.get(source=source, year=2024, problem_label="1").content.get().source_for("en"), "Incoming")

    def test_attachment_conflicts_require_per_item_policy(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            owner = make_staff(username="archive-owner-3")
            source = make_source(slug="imo", name="IMO")
            problem = make_problem(source=source, year=2024, problem_label="1", content="Statement")
            content = problem.content.get()
            ContentAttachment.from_upload(content, SimpleUploadedFile("target-only.png", b"old", content_type="image/png"))
            incoming = b"new"
            archive_file = "files/content_attachments/imo/2024/1/figure.png"
            archive = f"{tmp}/import.zip"
            self._write_archive(
                archive,
                sources=[{"key": "imo", "slug": "imo", "parent": None, "order": 0, "is_public": True, "translations": {"en": {"name": "IMO"}}, "tags": []}],
                problems=[self._problem_payload(
                    text="Incoming",
                    attachments=[{
                        "name": "figure.png",
                        "path": archive_file,
                        "content_type": "image/png",
                        "size": len(incoming),
                        "sha256": __import__("hashlib").sha256(incoming).hexdigest(),
                    }],
                )],
                files={archive_file: incoming},
            )

            plan = plan_import(archive, ImportOptions(owner=owner, existing_problems="overwrite"))

            self.assertFalse(plan.can_apply)
            self.assertEqual(
                {c.reason for c in plan.conflicts if c.selected_action is None},
                {"existing attachment is missing from archive"},
            )

            options = ImportOptions(owner=owner, existing_problems="overwrite", missing_attachments="delete", do_it=True)
            plan = plan_import(archive, options)
            self.assertTrue(plan.can_apply)
            apply_import(archive, options, plan)
            attachment_names = set(problem.content.get().attachments.values_list("name", flat=True))
            self.assertEqual(attachment_names, {"figure.png"})

    def test_import_command_json_dry_run(self):
        with TemporaryDirectory() as tmp:
            owner = make_staff(username="archive-cli-owner")
            archive = f"{tmp}/import.zip"
            self._write_archive(
                archive,
                sources=[{"key": "imo", "slug": "imo", "parent": None, "order": 0, "is_public": True, "translations": {"en": {"name": "IMO"}}, "tags": []}],
                problems=[self._problem_payload()],
            )
            out = StringIO()

            call_command("import_archive", archive, "--owner", owner.username, "--json", stdout=out)

            data = json.loads(out.getvalue())
            self.assertEqual(data["mode"], "dry_run")
            self.assertTrue(data["can_apply"])
            self.assertEqual(data["summary"]["create"]["problem"], 1)


class SourceAdminTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = make_staff(username="admin")
        cls.regular = make_user(username="reg")

    def test_create_requires_staff(self):
        self.client.force_login(self.regular)
        r = self.client.get("/archive/manage/new/")
        self.assertEqual(r.status_code, 403)

    def test_create_accessible_for_staff(self):
        self.client.force_login(self.staff)
        r = self.client.get("/archive/manage/new/")
        self.assertEqual(r.status_code, 200)

    def test_manage_sources_are_sorted_by_hierarchy(self):
        root = make_source(slug="admin-cro", name="Croatian Competitions")
        contest = make_source(slug="admin-national", name="Croatian National", parent=root)
        grade = make_source(slug="admin-grade-9", name="Grade 9", parent=contest)
        imo = make_source(slug="admin-imo", name="IMO")
        Source.objects.filter(pk=root.pk).update(order=10)
        Source.objects.filter(pk=contest.pk).update(order=5)
        Source.objects.filter(pk=grade.pk).update(order=1)
        Source.objects.filter(pk=imo.pk).update(order=20)
        self.client.force_login(self.staff)

        r = self.client.get("/archive/manage/")
        html = r.content.decode()

        self.assertLess(html.index("Croatian Competitions"), html.index("Croatian National"))
        self.assertLess(html.index("Croatian National"), html.index("Grade 9"))
        self.assertLess(html.index("Grade 9"), html.index("IMO"))

    def test_create_post_success(self):
        self.client.force_login(self.staff)
        r = self.client.post(
            "/archive/manage/new/",
            {
                "slug": "newsrc",
                "name_en": "New Source",
                "description_en": "",
                "parent": "",
                "order": "0",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Source.objects.filter(slug="newsrc").exists())

    def test_inline_create_requires_staff(self):
        self.client.force_login(self.regular)
        r = self.client.post(
            "/archive/manage/new-inline/",
            data=json.dumps({"slug": "inline", "name_en": "Inline"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)

    def test_inline_create_returns_source_payload(self):
        parent = make_source(slug="parent-inline", name="Parent Inline")
        self.client.force_login(self.staff)
        r = self.client.post(
            "/archive/manage/new-inline/",
            data=json.dumps({
                "slug": "inline-src",
                "name_en": "Inline Source",
                "name_hr": "Inline izvor",
                "parent": str(parent.pk),
            }),
            content_type="application/json",
        )

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["source"]["slug"], "inline-src")
        self.assertEqual(data["source"]["parentId"], parent.pk)
        source = Source.objects.get(slug="inline-src")
        self.assertEqual(source.parent, parent)
        self.assertEqual(source.translations["hr"]["name"], "Inline izvor")

    def test_create_missing_name_rejected(self):
        self.client.force_login(self.staff)
        r = self.client.post(
            "/archive/manage/new/",
            {"slug": "noname", "name_en": "", "order": "0"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Name")

    def test_edit_requires_staff(self):
        src = make_source(slug="edsrc", name="Ed")
        self.client.force_login(self.regular)
        r = self.client.get(f"/archive/manage/{src.pk}/edit/")
        self.assertEqual(r.status_code, 403)

    def test_edit_updates_tags_m2m(self):
        src = make_source(slug="tagedit", name="T")
        t1 = make_tag(slug="edt1", name="T1")
        t2 = make_tag(slug="edt2", name="T2")
        self.client.force_login(self.staff)
        r = self.client.post(
            f"/archive/manage/{src.pk}/edit/",
            {
                "action": "details",
                "slug": src.slug,
                "name_en": "T",
                "description_en": "",
                "parent": "",
                "order": "0",
                "tags": [t1.slug, t2.slug],
            },
        )
        self.assertEqual(r.status_code, 302)
        src.refresh_from_db()
        self.assertEqual(set(src.tags.all()), {t1, t2})

    def test_edit_page_contains_children_form(self):
        src = make_source(slug="parent-edit", name="Parent Edit")
        self.client.force_login(self.staff)

        r = self.client.get(f"/archive/manage/{src.pk}/edit/")

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Save children")
        self.assertContains(r, 'name="child_name_en"')

    def test_children_form_creates_child_sources(self):
        src = make_source(slug="parent-children", name="Parent Children")
        self.client.force_login(self.staff)

        r = self.client.post(
            f"/archive/manage/{src.pk}/edit/",
            {
                "action": "children",
                "child_id": ["", ""],
                "child_slug": ["grade-1", "grade-2"],
                "child_name_en": ["Grade 1", "Grade 2"],
                "child_name_hr": ["1. razred", "2. razred"],
                "child_order": ["10", "20"],
            },
        )

        self.assertEqual(r.status_code, 302)
        child = Source.objects.get(slug="grade-1")
        self.assertEqual(child.parent, src)
        self.assertEqual(child.translations["hr"]["name"], "1. razred")

    def test_children_form_updates_existing_child(self):
        src = make_source(slug="parent-update", name="Parent Update")
        child = make_source(slug="old-child", name="Old Child", parent=src)
        self.client.force_login(self.staff)

        r = self.client.post(
            f"/archive/manage/{src.pk}/edit/",
            {
                "action": "children",
                "child_id": [str(child.pk)],
                "child_slug": ["new-child"],
                "child_name_en": ["New Child"],
                "child_name_hr": [""],
                "child_order": ["30"],
            },
        )

        self.assertEqual(r.status_code, 302)
        child.refresh_from_db()
        self.assertEqual(child.slug, "new-child")
        self.assertEqual(child.order, 30)
