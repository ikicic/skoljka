import io
import json
import re
import time
import base64
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import pymupdf
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from skoljka.apps.content.models import ContentAttachment
from skoljka.apps.importer.backends import normalize_image_references
from skoljka.apps.importer.models import TranscriptionJob
from skoljka.apps.importer.tag_suggestions import suggest_tags_for_sources
from skoljka.apps.problems.models import Problem
from skoljka.apps.sources.models import Source, SourceDocument
from skoljka.apps.tags.models import Tag
from skoljka.tests.factories import make_source, make_staff, make_tag, make_user
from skoljka.transcription.crypto import encrypt_blob, file_key


def _make_pdf(pages: int = 3) -> bytes:
    """Return a minimal multi-page PDF as bytes."""
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page(width=200, height=200)
        page.insert_text((20, 50), f"Page {i + 1}")
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


class _StubBackend:
    """Test double for SandboxBackend: returns canned problems or raises."""

    def __init__(self, problems=None, delay=0.0, error=None):
        self.problems = problems or []
        self.delay = delay
        self.error = error
        self.calls: list[int] = []

    def transcribe(self, pdf_bytes: bytes, source_context=None, progress=None) -> list[dict]:
        self.calls.append((len(pdf_bytes), source_context))
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise self.error
        if progress:
            progress("ocr", "running")
            progress("ocr", "done")
            progress("llm", "running")
            progress("llm", "done")
        return self.problems


class _MemoryCache:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def put(self, key, value):
        self.data[key] = value


class _StubChatProvider:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def structured_chat(self, system, content, model, schema):
        self.calls.append((system, content, model, schema))
        return self.payload


class ImporterStaffGatingTest(TestCase):
    def test_pdf_import_get_requires_staff(self):
        user = make_user(username="ig")
        self.client.force_login(user)
        r = self.client.get("/problems/import/pdf/")
        self.assertEqual(r.status_code, 403)

    def test_pdf_import_get_staff_ok(self):
        staff = make_staff(username="igok")
        self.client.force_login(staff)
        r = self.client.get("/problems/import/pdf/")
        self.assertEqual(r.status_code, 200)

    def test_pdf_import_sources_are_sorted_by_hierarchy(self):
        staff = make_staff(username="import-source-order")
        root = make_source(slug="cro", name="Croatian Competitions")
        contest = make_source(slug="cro-national", name="Croatian National", parent=root)
        grade = make_source(slug="cro-grade-9", name="Grade 9", parent=contest)
        imo = make_source(slug="imo", name="IMO")
        Source.objects.filter(pk=root.pk).update(order=10)
        Source.objects.filter(pk=contest.pk).update(order=5)
        Source.objects.filter(pk=grade.pk).update(order=1)
        Source.objects.filter(pk=imo.pk).update(order=20)
        self.client.force_login(staff)

        r = self.client.get("/problems/import/pdf/")
        html = r.content.decode()
        match = re.search(r'<script type="application/json" id="pdf-sources-data">\s*(.*?)\s*</script>', html, re.S)
        self.assertIsNotNone(match)
        sources = json.loads(match.group(1))

        self.assertEqual([s["id"] for s in sources], [root.pk, contest.pk, grade.pk, imo.pk])
        self.assertEqual([s["depth"] for s in sources], [0, 1, 2, 0])

    def test_pdf_import_does_not_default_language(self):
        staff = make_staff(username="iglang")
        self.client.force_login(staff)
        r = self.client.get("/problems/import/pdf/")
        self.assertNotContains(r, "data-language=")

    def test_confirm_requires_staff(self):
        user = make_user(username="ic")
        self.client.force_login(user)
        r = self.client.post(
            "/problems/import/pdf/confirm/",
            data=json.dumps({"problems": [{"source_md": "x"}]}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)


class PdfConfirmTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = make_staff(username="imp")
        cls.src = make_source(slug="imo", name="IMO")
        cls.tag = make_tag(slug="imotag", name="ImoTag")

    def setUp(self):
        self.client.force_login(self.staff)

    def _post(self, data):
        return self.client.post(
            "/problems/import/pdf/confirm/",
            data=json.dumps(data),
            content_type="application/json",
        )

    def test_creates_problems_with_sequential_numbers(self):
        r = self._post(
            {
                "source_id": self.src.pk,
                "year": 2024,
                "language": "en",
                "global_tags": [self.tag.slug],
                "problems": [
                    {"source_md": "First statement."},
                    {"source_md": "Second statement."},
                ],
            }
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["created"], 2)
        self.assertEqual(len(data["ids"]), 2)
        self.assertEqual(data["redirect_url"], "/archive/imo/2024/")
        p1 = Problem.objects.get(pk=data["ids"][0])
        self.assertEqual(p1.year, 2024)
        self.assertEqual(p1.problem_label, "1")
        self.assertIn(self.tag, p1.tags.all())

    def test_creates_content_rows(self):
        r = self._post(
            {
                "source_id": self.src.pk,
                "year": 2024,
                "language": "en",
                "problems": [{"source_md": "Stmt body"}],
            }
        )
        p = Problem.objects.get(pk=r.json()["ids"][0])
        c = p.content.get()
        self.assertIn("Stmt body", c.html_for("en"))

    def test_can_assign_problem_to_child_source(self):
        child = make_source(slug="imo-grade-1", name="IMO Grade 1", parent=self.src)
        r = self._post(
            {
                "source_id": self.src.pk,
                "year": 2024,
                "language": "en",
                "problems": [{"source_id": child.pk, "problem_label": "3", "source_md": "Stmt body"}],
            }
        )
        self.assertEqual(r.status_code, 200)
        p = Problem.objects.get(pk=r.json()["ids"][0])
        self.assertEqual(p.source, child)
        self.assertEqual(p.problem_label, "3")

    def test_rejects_problem_source_outside_selected_source_context(self):
        other = make_source(slug="outside-import-context", name="Outside Import Context")

        r = self._post(
            {
                "source_id": self.src.pk,
                "year": 2024,
                "language": "en",
                "problems": [{"source_id": other.pk, "problem_label": "3", "source_md": "Stmt body"}],
            }
        )

        self.assertEqual(r.status_code, 400)
        self.assertEqual(Problem.objects.count(), 0)

    def test_rejects_selected_source_that_does_not_match_job_context(self):
        other = make_source(slug="other-job-context", name="Other Job Context")
        job = TranscriptionJob.objects.create(
            user=self.staff,
            pdf_ciphertext=b"x",
            status=TranscriptionJob.Status.DONE,
            source_context_json=json.dumps({
                "default_source_key": other.slug,
                "allowed_sources": [{"key": other.slug, "id": other.pk, "name": other.name()}],
            }),
        )

        r = self._post(
            {
                "source_id": self.src.pk,
                "job_id": str(job.pk),
                "year": 2024,
                "language": "en",
                "problems": [{"source_md": "Stmt body"}],
            }
        )

        self.assertEqual(r.status_code, 400)
        self.assertEqual(Problem.objects.count(), 0)

    def test_duplicates_are_allowed(self):
        """Re-importing the same (source, year, problem_label) creates a second row."""
        first = self._post(
            {
                "source_id": self.src.pk,
                "year": 2024,
                "language": "en",
                "problems": [{"source_md": "first"}],
            }
        )
        self.assertEqual(first.status_code, 200)
        second = self._post(
            {
                "source_id": self.src.pk,
                "year": 2024,
                "language": "en",
                "problems": [{"source_md": "second"}],
            }
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Problem.objects.filter(source=self.src, year=2024, problem_label="1").count(), 2)

    def test_invalid_source_id_returns_400(self):
        r = self._post(
            {
                "source_id": 999999,
                "year": 2024,
                "language": "en",
                "problems": [{"source_md": "x"}],
            }
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Problem.objects.count(), 0)

    def test_missing_source_id_returns_400(self):
        r = self._post(
            {
                "language": "en",
                "problems": [{"source_md": "x"}],
            }
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Problem.objects.count(), 0)

    def test_invalid_tag_slug_silently_skipped(self):
        """Invalid global tag slugs are filtered out (not an error)."""
        r = self._post(
            {
                "source_id": self.src.pk,
                "year": 2024,
                "language": "en",
                "global_tags": ["missing-tag"],
                "problems": [{"source_md": "x"}],
            }
        )
        self.assertEqual(r.status_code, 200)
        p = Problem.objects.get(pk=r.json()["ids"][0])
        self.assertEqual(list(p.tags.all()), [])

    def test_creates_new_tags(self):
        r = self._post(
            {
                "source_id": self.src.pk,
                "year": 2024,
                "language": "en",
                "global_new_tags": ["New Topic"],
                "problems": [{"source_md": "x", "new_tags": ["Local Topic"]}],
            }
        )
        self.assertEqual(r.status_code, 200)
        p = Problem.objects.get(pk=r.json()["ids"][0])
        self.assertEqual(
            set(p.tags.values_list("slug", flat=True)),
            {"new-topic", "local-topic"},
        )

    def test_empty_problems_returns_400(self):
        r = self._post({"source_id": self.src.pk, "year": 2024, "problems": []})
        self.assertEqual(r.status_code, 400)

    def test_invalid_json_returns_400(self):
        r = self.client.post(
            "/problems/import/pdf/confirm/",
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_wrong_json_shape_returns_400_without_creating_tags(self):
        r = self._post(
            {
                "source_id": self.src.pk,
                "year": 2024,
                "language": "en",
                "global_new_tags": ["Should Roll Back"],
                "problems": ["not an object"],
            }
        )

        self.assertEqual(r.status_code, 400)
        self.assertEqual(Problem.objects.count(), 0)
        self.assertFalse(Tag.objects.filter(slug="should-roll-back").exists())

    def test_invalid_year_returns_400(self):
        r = self._post(
            {
                "source_id": self.src.pk,
                "year": ["2024"],
                "language": "en",
                "problems": [{"source_md": "x"}],
            }
        )

        self.assertEqual(r.status_code, 400)
        self.assertEqual(Problem.objects.count(), 0)

    def test_invalid_document_source_url_returns_400(self):
        r = self._post(
            {
                "source_id": self.src.pk,
                "year": 2024,
                "language": "en",
                "document_source_url": "not a url",
                "problems": [{"source_md": "x"}],
            }
        )

        self.assertEqual(r.status_code, 400)
        self.assertEqual(Problem.objects.count(), 0)

    def test_redirect_url_without_year(self):
        r = self._post(
            {
                "source_id": self.src.pk,
                "language": "en",
                "problems": [{"source_md": "x"}],
            }
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["redirect_url"], "/archive/imo/")

    def test_promotes_original_pdf_from_job(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            job = TranscriptionJob.objects.create(
                user=self.staff,
                pdf_ciphertext=b"x",
                status=TranscriptionJob.Status.DONE,
                original_filename="contest.pdf",
            )
            job.original_pdf.save("contest.pdf", ContentFile(b"%PDF full original"), save=True)

            r = self._post(
                {
                    "source_id": self.src.pk,
                    "job_id": str(job.pk),
                    "year": 2024,
                    "language": "hr",
                    "document_source_url": "https://example.com/contest.pdf",
                    "problems": [{"source_md": "Stmt"}],
                }
            )

            self.assertEqual(r.status_code, 200)
            document = SourceDocument.objects.get(pk=r.json()["document_id"])
            self.assertEqual(document.source, self.src)
            self.assertEqual(document.year, 2024)
            self.assertEqual(document.language, "hr")
            self.assertEqual(document.original_filename, "contest.pdf")
            self.assertEqual(document.source_url, "https://example.com/contest.pdf")
            document.file.open("rb")
            self.assertEqual(document.file.read(), b"%PDF full original")
            document.file.close()
            job.refresh_from_db()
            self.assertFalse(job.original_pdf)

    def test_promoted_original_pdf_storage_name_is_safe(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            job = TranscriptionJob.objects.create(
                user=self.staff,
                pdf_ciphertext=b"x",
                status=TranscriptionJob.Status.DONE,
                original_filename="../unsafe/contest.pdf",
            )
            job.original_pdf.save("../unsafe/contest.pdf", ContentFile(b"%PDF full original"), save=True)

            r = self._post(
                {
                    "source_id": self.src.pk,
                    "job_id": str(job.pk),
                    "year": 2024,
                    "language": "hr",
                    "problems": [{"source_md": "Stmt"}],
                }
            )

            self.assertEqual(r.status_code, 200)
            document = SourceDocument.objects.get(pk=r.json()["document_id"])
            self.assertTrue(document.file.name.startswith("documents/"))
            self.assertTrue(document.file.name.endswith("/contest.pdf"))
            self.assertNotIn("..", document.file.name)

    def test_confirm_imports_referenced_job_images_as_attachments(self):
        image_bytes = b"\x89PNG\r\n\x1a\nfigure"
        result = {
            "images": {
                "img-0.png": base64.b64encode(image_bytes).decode("ascii"),
                "unused.png": base64.b64encode(b"unused").decode("ascii"),
            },
            "problems": [],
        }
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            job = TranscriptionJob.objects.create(
                user=self.staff,
                pdf_ciphertext=b"x",
                status=TranscriptionJob.Status.DONE,
                result_ciphertext=encrypt_blob(json.dumps(result).encode(), file_key()),
            )

            r = self._post(
                {
                    "source_id": self.src.pk,
                    "job_id": str(job.pk),
                    "year": 2024,
                    "language": "en",
                    "problems": [{"source_md": "See ![figure](attachment:img-0.png){width=50%}."}],
                }
            )

            self.assertEqual(r.status_code, 200)
            problem = Problem.objects.get(pk=r.json()["ids"][0])
            content = problem.content.get()
            attachment = ContentAttachment.objects.get(content=content)
            self.assertEqual(attachment.name, "img-0.png")
            attachment.file.open("rb")
            self.assertEqual(attachment.file.read(), image_bytes)
            attachment.file.close()
            self.assertIn("/media/", content.html_for("en"))
            self.assertNotIn("attachment:img-0.png", content.html_for("en"))
            self.assertFalse(ContentAttachment.objects.filter(name="unused.png").exists())

    def test_confirm_does_not_import_job_image_when_reference_was_removed(self):
        result = {
            "images": {
                "img-0.png": base64.b64encode(b"image").decode("ascii"),
            },
            "problems": [],
        }
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            job = TranscriptionJob.objects.create(
                user=self.staff,
                pdf_ciphertext=b"x",
                status=TranscriptionJob.Status.DONE,
                result_ciphertext=encrypt_blob(json.dumps(result).encode(), file_key()),
            )

            r = self._post(
                {
                    "source_id": self.src.pk,
                    "job_id": str(job.pk),
                    "year": 2024,
                    "language": "en",
                    "problems": [{"source_md": "The image reference was deleted."}],
                }
            )

            self.assertEqual(r.status_code, 200)
            problem = Problem.objects.get(pk=r.json()["ids"][0])
            content = problem.content.get()
            self.assertFalse(ContentAttachment.objects.filter(content=content).exists())
            self.assertEqual(content.source_for("en"), "The image reference was deleted.")


class ImageReferenceNormalizationTest(TestCase):
    def test_normalizes_known_markdown_images(self):
        source = "See ![diagram](img-0.png){width=50%} and ![other](other.png)."
        self.assertEqual(
            normalize_image_references(source, ["img-0.png"]),
            "See ![diagram](attachment:img-0.png){width=50%} and ![other](other.png).",
        )

    def test_normalizes_known_includegraphics(self):
        source = r"See \includegraphics[width=4cm]{img-0.png}."
        self.assertEqual(
            normalize_image_references(source, ["img-0.png"]),
            "See ![figure](attachment:img-0.png){width=25%}.",
        )


class TagSuggestionTest(TestCase):
    def test_suggests_topic_tags_and_filters_invalid_output(self):
        geometry = make_tag(slug="geometry", name="Geometry")
        hidden = make_tag(slug="induction", name="Induction", kind=Tag.Kind.TECHNIQUE, hidden=True)
        provider = _StubChatProvider({
            "suggestions": [
                {"index": 0, "tags": ["geometry", "unknown", "geometry", hidden.slug]},
                {"index": 4, "tags": ["geometry"]},
            ],
        })

        suggestions = suggest_tags_for_sources(
            ["Triangle statement."],
            model="anthropic/test-model",
            cache=_MemoryCache(),
            chat_provider=provider,
        )

        self.assertEqual(suggestions, [["geometry"]])
        self.assertEqual(len(provider.calls), 1)
        self.assertIn('"slug":"geometry"', provider.calls[0][0])
        self.assertNotIn('"slug":"induction"', provider.calls[0][0])
        self.assertIn("algebra, combinatorics, geometry, or number-theory", provider.calls[0][0])

    def test_suggestion_endpoint_returns_dense_tag_lists(self):
        self.client.force_login(make_staff())
        make_tag(slug="geometry", name="Geometry")
        with mock.patch(
            "skoljka.apps.importer.views.suggest_tags_for_sources",
            return_value=[["geometry"], []],
        ) as suggest:
            r = self.client.post(
                "/problems/import/pdf/suggest-tags/",
                data=json.dumps({
                    "problems": [
                        {"source_md": "Triangle."},
                        {"source_md": "No clear topic."},
                    ],
                }),
                content_type="application/json",
            )

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"tags": [["geometry"], []]})
        suggest.assert_called_once()

    def test_suggestion_endpoint_rejects_wrong_json_shape(self):
        self.client.force_login(make_staff())
        r = self.client.post(
            "/problems/import/pdf/suggest-tags/",
            data=json.dumps(["not an object"]),
            content_type="application/json",
        )

        self.assertEqual(r.status_code, 400)

    def test_generic_suggestion_endpoint_returns_dense_tag_lists(self):
        self.client.force_login(make_staff())
        with mock.patch(
            "skoljka.apps.problems.views.suggest_tags_for_sources",
            return_value=[["geometry"]],
        ) as suggest:
            r = self.client.post(
                "/problems/suggest-tags/",
                data=json.dumps({"problems": [{"source_md": "Triangle."}]}),
                content_type="application/json",
            )

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"tags": [["geometry"]]})
        suggest.assert_called_once()

    def test_generic_suggestion_endpoint_rejects_wrong_json_shape(self):
        self.client.force_login(make_staff())
        r = self.client.post(
            "/problems/suggest-tags/",
            data=json.dumps(["not an object"]),
            content_type="application/json",
        )

        self.assertEqual(r.status_code, 400)


class ImportJsonCommandTest(TestCase):
    def test_imports_tag_descriptions(self):
        data = {
            "tags": [
                {
                    "slug": "functional-equations",
                    "kind": "topic",
                    "translations": {"en": "Functional equations"},
                    "short_translations": {"en": "FE"},
                    "descriptions": {"en": "Equations whose unknowns are functions."},
                }
            ]
        }
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            path.write_text(json.dumps(data))
            call_command("import_json", path, stdout=io.StringIO())

        tag = Tag.objects.get(slug="functional-equations")
        self.assertEqual(tag.short_translations["en"], "FE")
        self.assertEqual(tag.descriptions["en"], "Equations whose unknowns are functions.")

    def test_warns_about_duplicate_tag_short_translations(self):
        data = {
            "tags": [
                {
                    "slug": "number-theory",
                    "kind": "topic",
                    "translations": {"en": "Number theory"},
                    "short_translations": {"en": "NT"},
                },
                {
                    "slug": "newton-theorem",
                    "kind": "topic",
                    "translations": {"en": "Newton theorem"},
                    "short_translations": {"en": "nt"},
                },
            ]
        }
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            path.write_text(json.dumps(data))
            stderr = io.StringIO()
            call_command("import_json", path, stdout=io.StringIO(), stderr=stderr)

        self.assertIn("duplicate short translation", stderr.getvalue())
        self.assertIn("number-theory, newton-theorem", stderr.getvalue())

    def test_imports_curated_tags(self):
        fixture_path = Path(__file__).resolve().parents[3] / "data" / "tags.json"
        call_command("import_json", fixture_path, stdout=io.StringIO())

        self.assertGreaterEqual(Tag.objects.count(), 80)
        self.assertEqual(Tag.objects.get(slug="triangle").parent.slug, "geometry")
        self.assertTrue(Tag.objects.get(slug="induction").hidden)
        self.assertEqual(Tag.objects.get(slug="solid-geometry").short_translations["en"], "3D")


class PdfSliceTest(TestCase):
    def test_slice_returns_requested_pages(self):
        from skoljka.apps.importer.pdf_slice import page_count, slice_pdf

        pdf = _make_pdf(pages=5)
        sliced = slice_pdf(pdf, [0, 2, 4])
        self.assertEqual(page_count(sliced), 3)

    def test_slice_dedupes_and_sorts(self):
        from skoljka.apps.importer.pdf_slice import page_count, slice_pdf

        pdf = _make_pdf(pages=3)
        sliced = slice_pdf(pdf, [2, 0, 2, 0])
        self.assertEqual(page_count(sliced), 2)

    def test_slice_drops_out_of_range(self):
        from skoljka.apps.importer.pdf_slice import page_count, slice_pdf

        pdf = _make_pdf(pages=2)
        sliced = slice_pdf(pdf, [0, 99])
        self.assertEqual(page_count(sliced), 1)

    def test_slice_rejects_empty(self):
        from skoljka.apps.importer.pdf_slice import slice_pdf

        pdf = _make_pdf(pages=2)
        with self.assertRaises(ValueError):
            slice_pdf(pdf, [42])


class _TranscriptionViewBase(TestCase):
    """Test base that stubs transcription and runs workers inline."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = make_staff(username="imp-transcribe")

    def setUp(self):
        self.client.force_login(self.staff)
        self.stub = _StubBackend(problems=[
            {"problem_label": "1", "source_md": "Statement one.", "set": ""},
            {"problem_label": "2", "source_md": "Statement two.", "set": ""},
        ])
        patcher_backend = mock.patch(
            "skoljka.apps.importer.backends.make_default_backend",
            return_value=self.stub,
        )
        patcher_backend.start()
        self.addCleanup(patcher_backend.stop)

        from skoljka.apps.importer.worker import run_job

        def _inline(job_id, backend):
            run_job(job_id, backend)

        patcher_thread = mock.patch(
            "skoljka.apps.importer.views.start_job_thread",
            side_effect=_inline,
        )
        patcher_thread.start()
        self.addCleanup(patcher_thread.stop)


def _upload(client, pdf_bytes: bytes, pages):
    source = make_source(slug=f"upload-src-{time.monotonic_ns()}", name="Upload Source")
    return client.post(
        "/problems/import/pdf/transcribe/",
        data={
            "pdf": io.BytesIO(pdf_bytes),
            "pages": json.dumps(pages),
            "source_id": str(source.pk),
        },
        format="multipart",
    )


class TranscribeCreateTest(_TranscriptionViewBase):
    def test_create_returns_job_id_and_runs_worker(self):
        r = _upload(self.client, _make_pdf(3), [0, 1])
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("id", data)
        job = _wait_terminal(data["id"])
        self.assertEqual(job.status, TranscriptionJob.Status.DONE)
        self.assertEqual(len(self.stub.calls), 1)
        self.assertEqual(self.stub.calls[0][1]["default_source_key"].startswith("upload-src-"), True)

    def test_missing_pdf_returns_400(self):
        r = self.client.post(
            "/problems/import/pdf/transcribe/",
            data={"pages": "[0]"},
        )
        self.assertEqual(r.status_code, 400)

    def test_missing_source_returns_400(self):
        r = self.client.post(
            "/problems/import/pdf/transcribe/",
            data={"pdf": io.BytesIO(_make_pdf(2)), "pages": "[0]"},
        )
        self.assertEqual(r.status_code, 400)

    def test_empty_pages_returns_400(self):
        r = _upload(self.client, _make_pdf(3), [])
        self.assertEqual(r.status_code, 400)

    def test_invalid_pages_json_returns_400(self):
        r = self.client.post(
            "/problems/import/pdf/transcribe/",
            data={"pdf": io.BytesIO(_make_pdf(2)), "pages": "not json"},
        )
        self.assertEqual(r.status_code, 400)

    def test_out_of_range_pages_return_400(self):
        r = _upload(self.client, _make_pdf(2), [42, 99])
        self.assertEqual(r.status_code, 400)

    def test_non_staff_gets_403(self):
        self.client.force_login(make_user(username="notstaff-t"))
        r = _upload(self.client, _make_pdf(2), [0])
        self.assertEqual(r.status_code, 403)

    def test_anon_gets_redirect(self):
        self.client.logout()
        r = _upload(self.client, _make_pdf(2), [0])
        self.assertEqual(r.status_code, 302)

    def test_stored_pdf_is_encrypted(self):
        r = _upload(self.client, _make_pdf(2), [0])
        job = TranscriptionJob.objects.get(pk=r.json()["id"])
        # %PDF header must not appear in stored ciphertext.
        self.assertNotIn(b"%PDF", bytes(job.pdf_ciphertext))

    def test_can_keep_full_original_pdf(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            source = make_source(slug="keep-pdf", name="Keep PDF")
            pdf = _make_pdf(2)
            r = self.client.post(
                "/problems/import/pdf/transcribe/",
                data={
                    "pdf": io.BytesIO(pdf),
                    "pages": json.dumps([0]),
                    "source_id": str(source.pk),
                    "keep_original_pdf": "1",
                },
                format="multipart",
            )

            self.assertEqual(r.status_code, 200)
            job = TranscriptionJob.objects.get(pk=r.json()["id"])
            self.assertTrue(job.original_pdf)
            job.original_pdf.open("rb")
            self.assertEqual(job.original_pdf.read(), pdf)
            job.original_pdf.close()

    def test_original_pdf_upload_name_cannot_escape_import_directory(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            source = make_source(slug="safe-original-pdf", name="Safe Original PDF")
            pdf = _make_pdf(2)
            upload = io.BytesIO(pdf)
            upload.name = "../unsafe/contest.pdf"
            r = self.client.post(
                "/problems/import/pdf/transcribe/",
                data={
                    "pdf": upload,
                    "pages": json.dumps([0]),
                    "source_id": str(source.pk),
                    "keep_original_pdf": "1",
                },
                format="multipart",
            )

            self.assertEqual(r.status_code, 200)
            job = TranscriptionJob.objects.get(pk=r.json()["id"])
            self.assertTrue(job.original_pdf.name.startswith(f"imports/original-pdfs/{job.pk}/"))
            self.assertTrue(job.original_pdf.name.endswith("/contest.pdf"))
            self.assertNotIn("..", job.original_pdf.name)

    def test_original_pdf_empty_when_not_requested(self):
        r = _upload(self.client, _make_pdf(2), [0])
        job = TranscriptionJob.objects.get(pk=r.json()["id"])
        self.assertFalse(job.original_pdf)


class TranscribeStatusTest(_TranscriptionViewBase):
    def test_status_returns_problems_when_done(self):
        r = _upload(self.client, _make_pdf(2), [0])
        job_id = r.json()["id"]
        _wait_terminal(job_id)
        r2 = self.client.get(f"/problems/import/pdf/transcribe/{job_id}/")
        self.assertEqual(r2.status_code, 200)
        data = r2.json()
        self.assertEqual(data["status"], "done")
        self.assertEqual(len(data["problems"]), 2)
        self.assertEqual(data["problems"][0]["source_md"], "Statement one.")
        self.assertEqual(data["progress"]["current"], None)
        self.assertEqual([step["status"] for step in data["progress"]["steps"]], ["done", "done"])

    def test_status_returns_error_on_failure(self):
        self.stub.error = RuntimeError("boom")
        r = _upload(self.client, _make_pdf(2), [0])
        job_id = r.json()["id"]
        _wait_terminal(job_id)
        r2 = self.client.get(f"/problems/import/pdf/transcribe/{job_id}/")
        data = r2.json()
        self.assertEqual(data["status"], "failed")
        self.assertIn("boom", data["error"])

    def test_status_404_for_other_user(self):
        r = _upload(self.client, _make_pdf(2), [0])
        job_id = r.json()["id"]
        _wait_terminal(job_id)
        self.client.force_login(make_staff(username="other-staff"))
        r2 = self.client.get(f"/problems/import/pdf/transcribe/{job_id}/")
        self.assertEqual(r2.status_code, 404)

    def test_zombie_running_job_marked_failed_on_read(self):
        job = TranscriptionJob.objects.create(
            user=self.staff,
            pdf_ciphertext=b"irrelevant",
            status=TranscriptionJob.Status.RUNNING,
        )
        old = timezone.now() - timedelta(minutes=60)
        TranscriptionJob.objects.filter(pk=job.pk).update(updated_at=old)
        r = self.client.get(f"/problems/import/pdf/transcribe/{job.id}/")
        data = r.json()
        self.assertEqual(data["status"], "failed")
        self.assertIn("timed out", data["error"].lower())


class TranscribeCancelTest(_TranscriptionViewBase):
    def test_cancel_pending_job(self):
        job = TranscriptionJob.objects.create(
            user=self.staff,
            pdf_ciphertext=b"x",
            status=TranscriptionJob.Status.PENDING,
        )
        r = self.client.post(f"/problems/import/pdf/transcribe/{job.id}/cancel/")
        self.assertEqual(r.status_code, 200)
        job.refresh_from_db()
        self.assertEqual(job.status, TranscriptionJob.Status.CANCELLED)

    def test_cancel_terminal_job_returns_404(self):
        job = TranscriptionJob.objects.create(
            user=self.staff,
            pdf_ciphertext=b"x",
            status=TranscriptionJob.Status.DONE,
        )
        r = self.client.post(f"/problems/import/pdf/transcribe/{job.id}/cancel/")
        self.assertEqual(r.status_code, 404)

    def test_cancel_other_users_job_returns_404(self):
        other = make_staff(username="oth-cancel")
        job = TranscriptionJob.objects.create(
            user=other,
            pdf_ciphertext=b"x",
            status=TranscriptionJob.Status.PENDING,
        )
        r = self.client.post(f"/problems/import/pdf/transcribe/{job.id}/cancel/")
        self.assertEqual(r.status_code, 404)


class TranscribeDeleteTest(_TranscriptionViewBase):
    def test_delete_terminal_job(self):
        for status in (
            TranscriptionJob.Status.DONE,
            TranscriptionJob.Status.FAILED,
            TranscriptionJob.Status.CANCELLED,
        ):
            job = TranscriptionJob.objects.create(
                user=self.staff,
                pdf_ciphertext=b"x",
                status=status,
            )
            r = self.client.post(f"/problems/import/pdf/transcribe/{job.id}/delete/")
            self.assertEqual(r.status_code, 200)
            self.assertFalse(TranscriptionJob.objects.filter(pk=job.pk).exists())

    def test_delete_terminal_job_removes_original_pdf(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            job = TranscriptionJob.objects.create(
                user=self.staff,
                pdf_ciphertext=b"x",
                status=TranscriptionJob.Status.DONE,
                original_filename="delete-me.pdf",
            )
            job.original_pdf.save("delete-me.pdf", ContentFile(b"%PDF temp"), save=True)
            path = Path(job.original_pdf.path)

            r = self.client.post(f"/problems/import/pdf/transcribe/{job.id}/delete/")

            self.assertEqual(r.status_code, 200)
            self.assertFalse(TranscriptionJob.objects.filter(pk=job.pk).exists())
            self.assertFalse(path.exists())

    def test_delete_active_job_returns_404(self):
        for status in (
            TranscriptionJob.Status.PENDING,
            TranscriptionJob.Status.RUNNING,
        ):
            job = TranscriptionJob.objects.create(
                user=self.staff,
                pdf_ciphertext=b"x",
                status=status,
            )
            r = self.client.post(f"/problems/import/pdf/transcribe/{job.id}/delete/")
            self.assertEqual(r.status_code, 404)
            self.assertTrue(TranscriptionJob.objects.filter(pk=job.pk).exists())

    def test_delete_other_users_job_returns_404(self):
        other = make_staff(username="oth-delete")
        job = TranscriptionJob.objects.create(
            user=other,
            pdf_ciphertext=b"x",
            status=TranscriptionJob.Status.DONE,
        )
        r = self.client.post(f"/problems/import/pdf/transcribe/{job.id}/delete/")
        self.assertEqual(r.status_code, 404)
        self.assertTrue(TranscriptionJob.objects.filter(pk=job.pk).exists())


class TranscribeActiveTest(_TranscriptionViewBase):
    def test_active_lists_pending_and_running(self):
        TranscriptionJob.objects.create(
            user=self.staff, pdf_ciphertext=b"x",
            status=TranscriptionJob.Status.PENDING,
        )
        TranscriptionJob.objects.create(
            user=self.staff, pdf_ciphertext=b"x",
            status=TranscriptionJob.Status.RUNNING,
        )
        TranscriptionJob.objects.create(
            user=self.staff, pdf_ciphertext=b"x",
            status=TranscriptionJob.Status.DONE,
        )
        r = self.client.get("/problems/import/pdf/transcribe/active/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["jobs"]), 2)

    def test_active_scoped_to_user(self):
        other = make_staff(username="oth-active")
        TranscriptionJob.objects.create(
            user=other, pdf_ciphertext=b"x",
            status=TranscriptionJob.Status.PENDING,
        )
        r = self.client.get("/problems/import/pdf/transcribe/active/")
        self.assertEqual(len(r.json()["jobs"]), 0)


class WorkerCancellationTest(_TranscriptionViewBase):
    def test_cancelled_before_worker_runs(self):
        """A pre-cancelled job is not processed."""
        from skoljka.apps.importer.worker import run_job

        from skoljka.apps.importer.pdf_slice import slice_pdf
        from skoljka.transcription.crypto import encrypt_blob, file_key

        sliced = slice_pdf(_make_pdf(2), [0])
        job = TranscriptionJob.objects.create(
            user=self.staff,
            pdf_ciphertext=encrypt_blob(sliced, file_key()),
        )
        TranscriptionJob.objects.filter(pk=job.pk).update(
            status=TranscriptionJob.Status.CANCELLED,
        )
        run_job(str(job.id), self.stub)
        self.assertEqual(self.stub.calls, [])
        job.refresh_from_db()
        self.assertEqual(job.status, TranscriptionJob.Status.CANCELLED)
        self.assertIsNone(job.result_ciphertext or None)


class CleanupCommandTest(TestCase):
    def test_deletes_expired_jobs(self):
        user = make_staff(username="cleaner")
        old = TranscriptionJob.objects.create(
            user=user, pdf_ciphertext=b"x",
            expires_at=timezone.now() - timedelta(days=1),
        )
        fresh = TranscriptionJob.objects.create(
            user=user, pdf_ciphertext=b"x",
            expires_at=timezone.now() + timedelta(days=1),
        )
        from django.core.management import call_command
        call_command("cleanup_transcription", verbosity=0)
        self.assertFalse(TranscriptionJob.objects.filter(pk=old.pk).exists())
        self.assertTrue(TranscriptionJob.objects.filter(pk=fresh.pk).exists())

    def test_deletes_expired_job_original_pdf_file(self):
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
            user = make_staff(username="cleaner-file")
            job = TranscriptionJob.objects.create(
                user=user,
                pdf_ciphertext=b"x",
                expires_at=timezone.now() - timedelta(days=1),
                original_filename="delete-me.pdf",
            )
            job.original_pdf.save("delete-me.pdf", ContentFile(b"%PDF temp"), save=True)
            path = Path(job.original_pdf.path)

            from django.core.management import call_command
            call_command("cleanup_transcription", verbosity=0)

            self.assertFalse(TranscriptionJob.objects.filter(pk=job.pk).exists())
            self.assertFalse(path.exists())


def _wait_terminal(job_id: str, timeout: float = 5.0) -> TranscriptionJob:
    """Poll until the job reaches a terminal status or the timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = TranscriptionJob.objects.get(pk=job_id)
        if job.is_terminal():
            return job
        time.sleep(0.02)
    raise AssertionError(f"Job {job_id} did not reach terminal state within {timeout}s")
