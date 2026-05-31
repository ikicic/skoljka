"""Delete expired transcription jobs and cache entries."""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from skoljka.apps.importer.models import TranscriptionJob
from skoljka.transcription.cache import APICache


class Command(BaseCommand):
    help = "Delete expired transcription jobs and API cache rows."

    def handle(self, *args, **options) -> None:
        now = timezone.now()
        expired_jobs = list(TranscriptionJob.objects.filter(expires_at__lt=now).only("id", "original_pdf"))
        for job in expired_jobs:
            if job.original_pdf:
                job.original_pdf.delete(save=False)
        deleted, _ = TranscriptionJob.objects.filter(pk__in=[job.pk for job in expired_jobs]).delete()
        self.stdout.write(f"Deleted {deleted} expired TranscriptionJob rows.")

        cache_path = Path(settings.TRANSCRIPTION_PRIVATE_DIR) / "api_cache.sqlite"
        if cache_path.exists():
            cache = APICache(
                cache_path,
                ttl_seconds=settings.TRANSCRIPTION_TTL_DAYS * 86400,
            )
            n = cache.cleanup_expired()
            self.stdout.write(f"Deleted {n} expired APICache rows.")
        else:
            self.stdout.write("No API cache file present; skipping.")
