import subprocess
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from tempfile import TemporaryDirectory

from skoljka.apps.content.models import ContentAttachment
from skoljka.apps.problems.models import Problem
from skoljka.apps.problems.pdf_export import export_problems_latex_zip, export_problems_pdf
from skoljka.apps.tracking.models import Submission
from skoljka.tests.factories import (
    make_problem,
    make_source,
    make_staff,
    make_tag,
    make_user,
)


REAL_SUBPROCESS_RUN = subprocess.run


class ProblemModelTest(TestCase):
    def test_display_title_uses_title_when_set(self):
        p = make_problem(title="The Hat Problem")
        self.assertEqual(p.display_title, "The Hat Problem")

    def test_display_title_fallback_from_source(self):
        src = make_source(slug="imo", name="IMO")
        p = make_problem(source=src, year=2024, problem_label=3)
        self.assertEqual(p.display_title, "IMO 2024 Problem 3")

    def test_display_title_unnamed_fallback(self):
        p = make_problem()
        self.assertEqual(p.display_title, "(unnamed problem)")

    def test_tags_m2m(self):
        p = make_problem()
        t1 = make_tag(slug="algebra", name="Algebra")
        t2 = make_tag(slug="geo", name="Geometry")
        p.tags.add(t1, t2)
        self.assertEqual(set(p.tags.all()), {t1, t2})


class ProblemListViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = make_user(username="a")
        cls.bob = make_user(username="b")
        cls.public = make_problem(title="Public P", created_by=cls.alice)
        cls.private_alice = make_problem(
            title="Alice Private", created_by=cls.alice, is_public=False
        )
        cls.private_bob = make_problem(
            title="Bob Private", created_by=cls.bob, is_public=False
        )

    def test_anon_sees_only_public(self):
        r = self.client.get("/problems/")
        self.assertContains(r, self.public.title)
        self.assertNotContains(r, self.private_alice.title)
        self.assertNotContains(r, self.private_bob.title)

    def test_authenticated_sees_public_plus_own(self):
        self.client.force_login(self.alice)
        r = self.client.get("/problems/")
        self.assertContains(r, self.public.title)
        self.assertContains(r, self.private_alice.title)
        self.assertNotContains(r, self.private_bob.title)

    def test_problem_table_paginates(self):
        for i in range(55):
            make_problem(title=f"Paged {i:02d}")

        r = self.client.get("/problems/")

        self.assertNotContains(r, "Showing 1-10 of")
        self.assertContains(r, "page=2")

    def test_staff_sees_problem_list_actions(self):
        staff = make_staff(username="problem-staff")
        self.client.force_login(staff)

        r = self.client.get("/problems/")

        self.assertContains(r, 'href="/problems/manage/new/"')
        self.assertContains(r, ">Add problem</a>")
        self.assertContains(r, 'href="/problems/import/pdf/"')
        self.assertContains(r, ">Import</a>")

    def test_authenticated_problem_list_exposes_status_cell_data(self):
        self.client.force_login(self.alice)

        r = self.client.get("/problems/")

        self.assertContains(r, 'data-problem-actions=""')
        self.assertContains(r, f'data-problem-id="{self.public.pk}"')
        self.assertNotContains(r, "data-solve-url")

    def test_toggle_solved_status_cell_returns_updated_payload(self):
        self.client.force_login(self.alice)

        r = self.client.post(
            reverse("toggle_solved", kwargs={"pk": self.public.pk}),
            HTTP_HX_TARGET=f"problem-actions-{self.public.pk}",
        )

        self.assertEqual(r.status_code, 200)
        self.assertTrue(Submission.objects.get(user=self.alice, problem=self.public).solved)
        self.assertContains(r, 'data-status-payload=""')
        self.assertContains(r, 'data-solved="1"')

    def test_regular_user_does_not_see_problem_list_actions(self):
        user = make_user(username="problem-user")
        self.client.force_login(user)

        r = self.client.get("/problems/")

        self.assertNotContains(r, 'href="/problems/manage/new/"')
        self.assertNotContains(r, 'href="/problems/import/pdf/"')

    def test_pdf_button_requires_login(self):
        r = self.client.get("/problems/")
        self.assertNotContains(r, 'href="/problems/export/pdf/"')

        self.client.force_login(self.alice)
        r = self.client.get("/problems/")
        self.assertContains(r, 'href="/problems/export/pdf/"')


class ProblemPdfExportTest(TestCase):
    def _fake_xelatex(self, args, **kwargs):
        cwd = kwargs.get("cwd")
        if cwd is None:
            return REAL_SUBPROCESS_RUN(args, **kwargs)
        tex = (cwd / "problems.tex").read_text(encoding="utf-8")
        self.rendered_tex = tex
        (cwd / "problems.pdf").write_bytes(b"%PDF fake")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    def test_export_renders_statement_math_and_unicode(self):
        problem = make_problem(title="Županijsko", content="Ako je $a < b$, dokaži tvrdnju.")

        with patch("skoljka.apps.problems.pdf_export.run_external") as run:
            run.side_effect = self._fake_xelatex
            exported = export_problems_pdf([problem], title="Zadaci", filename="zadaci.pdf")

        self.assertEqual(exported.data, b"%PDF fake")
        self.assertIn(r"\noindent 1.\quad Ako je $a < b$", self.rendered_tex)
        self.assertNotIn(r"\problemheading{1. Županijsko}", self.rendered_tex)
        self.assertIn(r"$a < b$", self.rendered_tex)
        self.assertIn("fontspec", self.rendered_tex)

    def test_export_copies_attachment_paths(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            problem = make_problem(content="![figure](attachment:figure.png){width=50%}")
            content = problem.content.get()
            ContentAttachment.from_upload(content, SimpleUploadedFile("figure.png", b"png", content_type="image/png"))
            content.save()

            with patch("skoljka.apps.problems.pdf_export.run_external") as run:
                run.side_effect = self._fake_xelatex
                export_problems_pdf([problem], title="Figures", filename="figures.pdf")

        self.assertIn(r"\includegraphics[width=0.5\linewidth]{\detokenize{attachments/p1/figure.png}}", self.rendered_tex)

    def test_export_escapes_raw_latex(self):
        problem = make_problem(title=r"\input{title}", content=r"\input{secret}")

        with patch("skoljka.apps.problems.pdf_export.run_external") as run:
            run.side_effect = self._fake_xelatex
            export_problems_pdf([problem], title=r"\write18{bad}", filename="safe.pdf", heading_mode="number-title")

        self.assertIn(r"\textbackslash{}input\{title\}", self.rendered_tex)
        self.assertIn(r"\textbackslash{}input\{secret\}", self.rendered_tex)
        self.assertIn(r"\textbackslash{}write18\{bad\}", self.rendered_tex)

    def test_export_compacts_generated_source_year_titles(self):
        source = make_source(slug="imo", name="IMO")
        problem = make_problem(source=source, year=2024, problem_label=2, content="Statement")

        with patch("skoljka.apps.problems.pdf_export.run_external") as run:
            run.side_effect = self._fake_xelatex
            export_problems_pdf(
                [problem],
                title="IMO 2024",
                filename="imo-2024.pdf",
                compact_generated_titles_for=(source.pk, 2024),
                heading_mode="number-title",
            )

        self.assertIn(r"\problemheading{1. Problem 2}", self.rendered_tex)
        self.assertNotIn("IMO 2024 Problem 2", self.rendered_tex)

    def test_export_can_use_problem_labels_as_inline_headings(self):
        problem = make_problem(problem_label="A1", content="Shortlist statement.")

        with patch("skoljka.apps.problems.pdf_export.run_external") as run:
            run.side_effect = self._fake_xelatex
            export_problems_pdf(
                [problem],
                title="Shortlist",
                filename="shortlist.pdf",
                heading_mode="label",
            )

        self.assertIn(r"\noindent A1.\quad Shortlist statement.", self.rendered_tex)
        self.assertNotIn(r"\noindent 1.\quad", self.rendered_tex)

    def test_latex_zip_contains_compiler_inputs(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            problem = make_problem(title="With figure", content="![figure](attachment:figure.png){width=50%}")
            content = problem.content.get()
            ContentAttachment.from_upload(content, SimpleUploadedFile("figure.png", b"png", content_type="image/png"))
            content.save()

            exported = export_problems_latex_zip([problem], title="Figures", filename="figures.zip")

        with ZipFile(BytesIO(exported.data)) as zf:
            self.assertEqual(set(zf.namelist()), {"problems.tex", "attachments/p1/figure.png"})
            tex = zf.read("problems.tex").decode("utf-8")

        self.assertIn(r"\includegraphics[width=0.5\linewidth]{\detokenize{attachments/p1/figure.png}}", tex)

    def test_latex_zip_namespaces_attachment_paths_by_problem(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            first = make_problem(content="![first](attachment:figure.png)")
            first_content = first.content.get()
            ContentAttachment.from_upload(first_content, SimpleUploadedFile("figure.png", b"first", content_type="image/png"))
            first_content.save()

            second = make_problem(content="![second](attachment:figure.png)")
            second_content = second.content.get()
            ContentAttachment.from_upload(second_content, SimpleUploadedFile("figure.png", b"second", content_type="image/png"))
            second_content.save()

            exported = export_problems_latex_zip([first, second], title="Figures", filename="figures.zip")

        with ZipFile(BytesIO(exported.data)) as zf:
            self.assertEqual(
                set(zf.namelist()),
                {"problems.tex", "attachments/p1/figure.png", "attachments/p2/figure.png"},
            )
            tex = zf.read("problems.tex").decode("utf-8")
            self.assertEqual(zf.read("attachments/p1/figure.png"), b"first")
            self.assertEqual(zf.read("attachments/p2/figure.png"), b"second")

        self.assertIn(r"\detokenize{attachments/p1/figure.png}", tex)
        self.assertIn(r"\detokenize{attachments/p2/figure.png}", tex)


class ProblemDetailViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = make_user(username="a")
        cls.bob = make_user(username="b")
        cls.staff = make_staff(username="s")
        cls.public = make_problem(content="Statement here")
        cls.private = make_problem(
            created_by=cls.alice, is_public=False, content="Secret"
        )
        cls.tag = make_tag(slug="combo", name="Combinatorics")
        cls.public.tags.add(cls.tag)

    def test_public_visible_to_anon(self):
        r = self.client.get(f"/problems/{self.public.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Statement here")

    def test_public_shows_tags(self):
        r = self.client.get(f"/problems/{self.public.id}/")
        self.assertContains(r, "Combinatorics")

    def test_public_shows_actions_when_authenticated(self):
        self.client.force_login(self.alice)
        r = self.client.get(f"/problems/{self.public.id}/")
        self.assertContains(r, "Mark solved")

    def test_public_no_actions_for_anon(self):
        r = self.client.get(f"/problems/{self.public.id}/")
        self.assertNotContains(r, "Mark solved")

    def test_private_hidden_from_non_owner(self):
        self.client.force_login(self.bob)
        r = self.client.get(f"/problems/{self.private.id}/")
        self.assertEqual(r.status_code, 404)

    def test_private_visible_to_owner(self):
        self.client.force_login(self.alice)
        r = self.client.get(f"/problems/{self.private.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Secret")

    def test_private_visible_to_staff(self):
        self.client.force_login(self.staff)
        r = self.client.get(f"/problems/{self.private.id}/")
        self.assertEqual(r.status_code, 200)

    def test_unknown_id_404(self):
        r = self.client.get("/problems/999999/")
        self.assertEqual(r.status_code, 404)

    def test_shows_attachments(self):
        with TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
                problem = make_problem(content="Statement with figure.")
                content = problem.content.get()
                ContentAttachment.from_upload(
                    content,
                    SimpleUploadedFile(
                        "figure.png",
                        b"png",
                        content_type="image/png",
                    ),
                )

                r = self.client.get(f"/problems/{problem.id}/")
                self.assertContains(r, "figure.png")
                self.assertContains(r, "3 B")
                self.assertContains(r, "problem-attachment-list")

    def test_generated_title_breadcrumb_links_year_and_shortens_problem_label(self):
        source = make_source(slug="imo", name="International Mathematical Olympiad")
        problem = make_problem(source=source, year=2024, problem_label=2)

        r = self.client.get(f"/problems/{problem.id}/")

        html = r.content.decode()
        breadcrumb = html.split('<nav class="breadcrumb">', 1)[1].split("</nav>", 1)[0]
        self.assertIn('href="/archive/imo/2024/">2024</a>', breadcrumb)
        self.assertIn("<span>Problem 2</span>", breadcrumb)
        self.assertNotIn("International Mathematical Olympiad 2024 Problem 2", breadcrumb)


class ProblemAdminTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = make_staff(username="admin")
        cls.regular = make_user(username="reg")

    def test_create_requires_staff_redirects_anon(self):
        r = self.client.get("/problems/manage/new/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r.url)

    def test_create_forbidden_for_regular_user(self):
        self.client.force_login(self.regular)
        r = self.client.get("/problems/manage/new/")
        self.assertEqual(r.status_code, 403)

    def test_create_accessible_for_staff(self):
        self.client.force_login(self.staff)
        r = self.client.get("/problems/manage/new/")
        self.assertEqual(r.status_code, 200)

    def test_create_post_creates_problem_and_content(self):
        self.client.force_login(self.staff)
        tag = make_tag(slug="algebra", name="Algebra")
        r = self.client.post(
            "/problems/manage/new/",
            {
                "title": "Brand new",
                "source": "",
                "year": "2024",
                "problem_label": "1",
                "original_language": "en",
                "new_lang": "en",
                "new_md": "Statement body",
                "tags": [tag.slug],
                "new_tags": ["New Topic"],
            },
        )
        self.assertEqual(r.status_code, 302)
        problem = Problem.objects.get(title="Brand new")
        content = problem.content.get()
        self.assertIn("Statement body", content.html_for("en"))
        self.assertEqual(
            set(problem.tags.values_list("slug", flat=True)),
            {"algebra", "new-topic"},
        )

    def test_create_post_does_not_upload_content_attachment(self):
        with TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
                self.client.force_login(self.staff)
                r = self.client.post(
                    "/problems/manage/new/",
                    {
                        "title": "With figure",
                        "source": "",
                        "year": "2024",
                        "problem_label": "1",
                        "new_lang": "",
                        "new_md": "See figure.",
                        "new_attachments": SimpleUploadedFile(
                            "figure.png",
                            b"png",
                            content_type="image/png",
                        ),
                    },
                )
                self.assertEqual(r.status_code, 302)
                problem = Problem.objects.get(title="With figure")
                content = problem.content.get()
                self.assertFalse(content.attachments.exists())

    def test_edit_adds_language_variant(self):
        self.client.force_login(self.staff)
        p = make_problem(content="EN text", language="en")
        r = self.client.post(
            f"/problems/manage/{p.id}/edit/",
            {
                "title": "",
                "source": "",
                "year": "",
                "problem_label": "",
                "original_language": "en",
                "existing_lang": "en",
                "content_md_en": "EN text",
                "new_lang": "hr",
                "new_md": "HR text",
            },
        )
        self.assertEqual(r.status_code, 302)
        content = p.content.get()
        self.assertEqual(p.content.count(), 1)
        self.assertEqual(content.source_for("hr"), "HR text")

    def test_edit_uploads_content_attachment(self):
        with TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
                self.client.force_login(self.staff)
                p = make_problem(content="EN text", language="en")
                content = p.content.get()
                r = self.client.post(
                    f"/problems/manage/{p.id}/edit/",
                    {
                        "title": "",
                        "source": "",
                        "year": "",
                        "problem_label": "",
                        "existing_lang": "en",
                        "content_md_en": "EN text",
                        f"content_attachments_{content.id}": SimpleUploadedFile(
                            "figure.png",
                            b"png",
                            content_type="image/png",
                        ),
                    },
                )
                self.assertEqual(r.status_code, 302)
                attachment = content.attachments.get()
                self.assertEqual(attachment.name, "figure.png")

    def test_edit_removes_language_variant_when_blanked(self):
        self.client.force_login(self.staff)
        p = make_problem(content="EN text", language="en")
        r = self.client.post(
            f"/problems/manage/{p.id}/edit/",
            {
                "title": "",
                "source": "",
                "year": "",
                "problem_label": "",
                "original_language": "en",
                "existing_lang": "en",
                "content_md_en": "",
                "new_lang": "",
                "new_md": "",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(p.content.count(), 0)

    def test_edit_requires_staff(self):
        p = make_problem()
        self.client.force_login(self.regular)
        r = self.client.get(f"/problems/manage/{p.id}/edit/")
        self.assertEqual(r.status_code, 403)

    def test_edit_links_to_delete_page(self):
        self.client.force_login(self.staff)
        p = make_problem(title="Delete Link")

        r = self.client.get(f"/problems/manage/{p.id}/edit/")

        self.assertContains(r, f'href="/problems/manage/{p.id}/delete/"')
        self.assertContains(r, ">Delete</a>")

    def test_delete_requires_staff(self):
        p = make_problem()
        self.client.force_login(self.regular)

        r = self.client.get(f"/problems/manage/{p.id}/delete/")

        self.assertEqual(r.status_code, 403)

    def test_delete_confirmation_deletes_problem(self):
        self.client.force_login(self.staff)
        p = make_problem(title="Delete Me", content="Gone")

        r = self.client.get(f"/problems/manage/{p.id}/delete/")
        self.assertContains(r, "Delete Me")
        self.assertContains(r, "Are you sure you want to delete this problem?")

        r = self.client.post(f"/problems/manage/{p.id}/delete/")

        self.assertRedirects(r, "/problems/manage/")
        self.assertFalse(Problem.objects.filter(pk=p.pk).exists())
