from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import IntegrityError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse
from tempfile import TemporaryDirectory

from skoljka.apps.content.admin import ContentAdmin
from skoljka.apps.content.models import Content, ContentAttachment
from skoljka.apps.problems.models import Problem
from skoljka.tests.factories import make_content, make_problem, make_staff, make_user


class ContentSaveTest(TestCase):
    def test_save_populates_compiled_html(self):
        p = make_problem()
        c = make_content(p, source_md="**bold**")
        self.assertIn("<strong>bold</strong>", c.html_for("en"))

    def test_save_populates_compiled_html_with_katex(self):
        p = make_problem()
        c = make_content(p, source_md="Let $x^2$ be given.")
        self.assertIn('class="katex"', c.html_for("en"))
        self.assertIn('<annotation encoding="application/x-tex">x^2</annotation>', c.html_for("en"))
        self.assertNotIn("$x^2$", c.html_for("en"))

    def test_save_populates_search_text(self):
        p = make_problem()
        c = make_content(p, source_md="**bold** text")
        self.assertEqual(c.search_text, "bold text")

    def test_unique_per_object(self):
        p = make_problem()
        make_content(p, source_md="A", language="en")
        with self.assertRaises(IntegrityError):
            Content.objects.create(content_object=p, source_md={"en": "A again"})

    def test_same_content_can_hold_multiple_languages(self):
        p = make_problem()
        c = make_content(p, source_md="Hello", language="en")
        c.set_text("hr", "Zdravo")
        c.save()
        self.assertEqual(p.content.count(), 1)
        self.assertEqual(c.source_for("hr"), "Zdravo")


class ContentFormatHelpTest(TestCase):
    def test_help_index_links_to_format_help(self):
        r = self.client.get(reverse("help_index"))
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn("Help", html)
        self.assertIn(reverse("help_format"), html)
        self.assertIn("Input format", html)

    def test_format_help_page_shows_examples(self):
        r = self.client.get(reverse("help_format"))
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn("Input format", html)
        self.assertIn(r"\textbf{bold}", html)
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_format_help_page_uses_croatian_examples(self):
        r = self.client.get(reverse("help_format"), HTTP_ACCEPT_LANGUAGE="hr")
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn("Format unosa", html)
        self.assertIn(r"\textbf{podebljano}", html)
        self.assertIn("<strong>podebljano</strong>", html)
        self.assertIn("Prvi odlomak", html)

    def test_content_editor_links_to_format_help(self):
        staff = make_staff()
        self.client.force_login(staff)
        r = self.client.get(reverse("problem_create"))
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn(reverse("help_format"), html)
        self.assertIn("Input format help", html)


class ProblemGetContentTest(TestCase):
    def test_content_returns_requested_language(self):
        p = make_problem()
        c = make_content(p, source_md="EN", language="en")
        c.set_text("hr", "HR")
        c.save()
        self.assertEqual(p.get_content("hr").source_for("hr"), "HR")

    def test_fallback_to_original_language(self):
        p = make_problem()
        c = make_content(p, source_md="HR", language="hr")
        self.assertEqual(c.source_for("fr"), "HR")

    def test_fallback_to_any_available(self):
        p = make_problem()
        c = make_content(p, source_md="EN", language="en")
        c.original_language = "de"
        c.save()
        self.assertEqual(c.source_for("fr"), "EN")

    def test_returns_none_when_no_content(self):
        p = make_problem()
        self.assertIsNone(p.get_content())


class ContentCascadeDeleteTest(TestCase):
    def test_deleting_problem_cascades_content(self):
        p = make_problem()
        make_content(p)
        self.assertEqual(Content.objects.count(), 1)
        Problem.objects.filter(pk=p.pk).delete()
        self.assertEqual(Content.objects.count(), 0)


class ContentAdminTest(TestCase):
    def test_rebuild_compiled_html_action_resaves_selected_content(self):
        problem = make_problem()
        content = make_content(problem, source_md=r"\textbf{Bold}")
        content.compiled_html = {"en": "<p>stale</p>"}
        content.search_text = "stale"
        content.save(update_fields=["compiled_html", "search_text"])

        request = RequestFactory().post("/admin/content/content/")
        request.user = make_staff()
        request.session = {}
        request._messages = FallbackStorage(request)
        admin = ContentAdmin(Content, AdminSite())

        admin.rebuild_compiled_html(request, Content.objects.filter(pk=content.pk))

        content.refresh_from_db()
        self.assertIn("<strong>Bold</strong>", content.html_for("en"))
        self.assertEqual(content.search_text, "Bold")


class SearchTextTest(TestCase):
    def test_html_entities_collapsed(self):
        p = make_problem()
        c = make_content(p, source_md="$a < b$")
        self.assertEqual(c.search_text, "$a < b$")

    def test_whitespace_normalized(self):
        p = make_problem()
        c = make_content(p, source_md="line one\n\nline two")
        self.assertEqual(c.search_text, "line one line two")

    def test_math_blocks_preserved(self):
        p = make_problem()
        c = make_content(p, source_md="Let $x$ be here.")
        self.assertIn("$x$", c.search_text)


class ContentAttachmentTest(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.tmp.name, MEDIA_URL="/media/")
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        self.tmp.cleanup()

    def test_attachment_names_are_unique_per_content(self):
        p = make_problem()
        c = make_content(p)
        ContentAttachment.from_upload(
            c,
            SimpleUploadedFile("figure.png", b"one", content_type="image/png"),
        )
        second = ContentAttachment.from_upload(
            c,
            SimpleUploadedFile("figure.png", b"two", content_type="image/png"),
        )
        self.assertEqual(second.name, "figure-2.png")

    def test_attachment_upload_name_cannot_escape_content_directory(self):
        p = make_problem()
        c = make_content(p)
        attachment = ContentAttachment.from_upload(
            c,
            SimpleUploadedFile("../unsafe/figure.png", b"png", content_type="image/png"),
        )

        self.assertEqual(attachment.name, "figure.png")
        self.assertIn(f"content/{c.pk}/attachments/figure.png", attachment.file.name)
        self.assertNotIn("..", attachment.file.name)

    def test_content_save_resolves_attachment_markdown_urls(self):
        p = make_problem()
        c = make_content(p, source_md="![figure](attachment:figure.png)")
        ContentAttachment.from_upload(
            c,
            SimpleUploadedFile("figure.png", b"png", content_type="image/png"),
        )
        c.save()
        self.assertIn('src="/media/content/', c.html_for("en"))
        self.assertNotIn("attachment:figure.png", c.html_for("en"))

    def test_content_save_resolves_sized_attachment_markdown_urls(self):
        p = make_problem()
        c = make_content(p, source_md="![figure](attachment:figure.png){width=50%}")
        ContentAttachment.from_upload(
            c,
            SimpleUploadedFile("figure.png", b"png", content_type="image/png"),
        )
        c.save()
        self.assertIn('src="/media/content/', c.html_for("en"))
        self.assertIn('style="width: 50%;"', c.html_for("en"))
        self.assertNotIn("attachment:figure.png", c.html_for("en"))

    def test_staff_can_upload_attachment_via_ajax_endpoint(self):
        staff = make_staff()
        self.client.force_login(staff)
        p = make_problem()
        c = make_content(p, source_md="![figure](attachment:figure.png)")

        r = self.client.post(
            f"/content/{c.id}/attachments/",
            {
                "files": SimpleUploadedFile(
                    "figure.png",
                    b"png",
                    content_type="image/png",
                ),
            },
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["attachments"][0]["name"], "figure.png")
        self.assertEqual(data["attachments"][0]["is_image"], True)
        self.assertTrue(c.attachments.filter(name="figure.png").exists())
        c.refresh_from_db()
        self.assertNotIn("attachment:figure.png", c.html_for("en"))

    def test_non_staff_cannot_upload_attachment_via_ajax_endpoint(self):
        user = make_user()
        self.client.force_login(user)
        p = make_problem()
        c = make_content(p)

        r = self.client.post(
            f"/content/{c.id}/attachments/",
            {
                "files": SimpleUploadedFile(
                    "figure.png",
                    b"png",
                    content_type="image/png",
                ),
            },
        )
        self.assertEqual(r.status_code, 403)
        self.assertFalse(c.attachments.exists())

    def test_staff_can_delete_attachment_via_ajax_endpoint(self):
        staff = make_staff()
        self.client.force_login(staff)
        p = make_problem()
        c = make_content(p, source_md="![figure](attachment:figure.png)")
        attachment = ContentAttachment.from_upload(
            c,
            SimpleUploadedFile("figure.png", b"png", content_type="image/png"),
        )
        c.save()

        r = self.client.delete(f"/content/{c.id}/attachments/{attachment.name}/")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(c.attachments.exists())
        c.refresh_from_db()
        self.assertIn("attachment:figure.png", c.html_for("en"))

    def test_non_staff_cannot_delete_attachment_via_ajax_endpoint(self):
        user = make_user()
        self.client.force_login(user)
        p = make_problem()
        c = make_content(p)
        attachment = ContentAttachment.from_upload(
            c,
            SimpleUploadedFile("figure.png", b"png", content_type="image/png"),
        )

        r = self.client.delete(f"/content/{c.id}/attachments/{attachment.name}/")
        self.assertEqual(r.status_code, 403)
        self.assertTrue(c.attachments.filter(name=attachment.name).exists())
