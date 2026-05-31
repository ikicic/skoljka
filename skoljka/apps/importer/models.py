import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils.text import get_valid_filename
from django.utils import timezone


def _default_expires_at():
    return timezone.now() + timedelta(days=settings.TRANSCRIPTION_TTL_DAYS)


def original_pdf_upload_to(instance: "TranscriptionJob", filename: str) -> str:
    filename = get_valid_filename(filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1])
    return f"imports/original-pdfs/{instance.id}/{filename or 'original.pdf'}"


class TranscriptionJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        RUNNING = "running"
        DONE = "done"
        FAILED = "failed"
        CANCELLED = "cancelled"

    TERMINAL = frozenset([Status.DONE, Status.FAILED, Status.CANCELLED])

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transcription_jobs",
    )
    # Encrypted PDF slice that contains only the pages selected for transcription.
    # This is always present because the worker transcribes this PDF, not the
    # original upload.
    pdf_ciphertext = models.BinaryField()
    # Optional full PDF uploaded by the user. This is populated only when the
    # import UI checkbox asks us to keep the whole original PDF on the website.
    # Empty means "transcribe the upload, but do not promote any archive PDF on
    # confirm"; it does not mean that /transcribe/ omitted the PDF upload.
    original_pdf = models.FileField(upload_to=original_pdf_upload_to, null=True, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    pages_json = models.TextField(default="[]")
    source_context_json = models.TextField(default="{}")
    progress_json = models.TextField(default='{"current":null,"steps":[]}')
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING,
    )
    result_ciphertext = models.BinaryField(null=True, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(default=_default_expires_at)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "updated_at"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"TranscriptionJob({self.id}, {self.status})"

    def is_terminal(self) -> bool:
        return self.status in self.TERMINAL
