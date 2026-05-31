"""Background transcription worker."""

import json
import logging
import threading

from django.db import connections
from django.utils import timezone

from skoljka.apps.importer.models import TranscriptionJob
from skoljka.transcription.crypto import decrypt_blob, encrypt_blob, file_key

logger = logging.getLogger(__name__)

_PROGRESS_STEPS = [
    {"key": "ocr", "label": "OCR"},
    {"key": "llm", "label": "LLM cleanup"},
]


def _progress_payload(statuses: dict[str, str]) -> dict:
    running = next((step["key"] for step in _PROGRESS_STEPS if statuses.get(step["key"]) == "running"), None)
    return {
        "current": running,
        "steps": [
            {**step, "status": statuses.get(step["key"], "pending")}
            for step in _PROGRESS_STEPS
        ],
    }


def run_job(job_id: str, backend_or_factory) -> None:
    progress_statuses = {step["key"]: "pending" for step in _PROGRESS_STEPS}

    def report_progress(key: str, status: str) -> None:
        if key not in progress_statuses:
            return
        progress_statuses[key] = status
        TranscriptionJob.objects.filter(pk=job_id, status=TranscriptionJob.Status.RUNNING).update(
            progress_json=json.dumps(_progress_payload(progress_statuses)),
            updated_at=timezone.now(),
        )

    try:
        affected = TranscriptionJob.objects.filter(
            pk=job_id, status=TranscriptionJob.Status.PENDING,
        ).update(
            status=TranscriptionJob.Status.RUNNING,
            progress_json=json.dumps(_progress_payload(progress_statuses)),
            updated_at=timezone.now(),
        )
        if not affected:
            return

        # Build the backend inside the worker thread.
        backend = backend_or_factory() if callable(backend_or_factory) else backend_or_factory

        job = TranscriptionJob.objects.get(pk=job_id)
        pdf_bytes = decrypt_blob(bytes(job.pdf_ciphertext), file_key())

        source_context = json.loads(job.source_context_json or "{}")
        result = backend.transcribe(pdf_bytes, source_context, report_progress)
        if isinstance(result, list):
            result = {"problems": result}

        # Honour cancellation before persisting the result.
        current_status = TranscriptionJob.objects.filter(pk=job_id).values_list("status", flat=True).first()
        if current_status != TranscriptionJob.Status.RUNNING:
            return

        result_json = json.dumps(result).encode("utf-8")
        progress_json = json.dumps(_progress_payload(progress_statuses))
        TranscriptionJob.objects.filter(pk=job_id, status=TranscriptionJob.Status.RUNNING).update(
            result_ciphertext=encrypt_blob(result_json, file_key()),
            progress_json=progress_json,
            status=TranscriptionJob.Status.DONE,
            updated_at=timezone.now(),
        )
    except Exception as exc:
        logger.exception("Transcription job %s failed", job_id)
        for key, status in list(progress_statuses.items()):
            if status == "running":
                progress_statuses[key] = "failed"
        try:
            TranscriptionJob.objects.filter(pk=job_id).update(
                status=TranscriptionJob.Status.FAILED,
                error=str(exc)[:2000],
                progress_json=json.dumps(_progress_payload(progress_statuses)),
                updated_at=timezone.now(),
            )
        except Exception:
            logger.exception("Could not mark job %s as failed", job_id)
    finally:
        # Tests may run this inline inside the main thread.
        if threading.current_thread() is not threading.main_thread():
            connections.close_all()


def start_job_thread(job_id: str, backend_or_factory) -> threading.Thread:
    t = threading.Thread(
        target=run_job,
        args=(job_id, backend_or_factory),
        name=f"transcription-{job_id}",
        daemon=True,
    )
    t.start()
    return t
