from __future__ import annotations

import hashlib
from pathlib import PurePosixPath

from django.utils.text import get_valid_filename

from skoljka.apps.problems.models import Problem


def problem_key(problem: Problem) -> str:
    source = problem.source.slug if problem.source else "none"
    year = str(problem.year) if problem.year is not None else "none"
    number = problem.problem_label or f"problem-{problem.pk}"
    return safe_component(f"{source}-{year}-{number}")


def document_key(source_slug: str, year: int | None, kind: str, filename: str) -> str:
    return safe_component(f"{source_slug}-{year if year is not None else 'none'}-{kind}-{filename}")


def attachment_archive_path(problem: Problem, filename: str) -> str:
    source = safe_component(problem.source.slug if problem.source else "none")
    year = safe_component(str(problem.year) if problem.year is not None else "none")
    number = safe_component(problem.problem_label or f"problem-{problem.pk}")
    return f"files/content_attachments/{source}/{year}/{number}/{safe_filename(filename)}"


def source_document_archive_path(source_slug: str, year: int | None, kind: str, filename: str) -> str:
    return f"files/source_documents/{safe_component(source_slug)}/{safe_component(str(year) if year is not None else 'none')}/{safe_component(kind)}/{safe_filename(filename)}"


def safe_component(value: str) -> str:
    return get_valid_filename(str(value).replace(":", "-")) or "item"


def safe_filename(value: str) -> str:
    return get_valid_filename(PurePosixPath(value).name.replace(":", "-")) or "file"


def safe_zip_path(path: str) -> bool:
    p = PurePosixPath(path)
    return bool(path) and not p.is_absolute() and ".." not in p.parts and p.parts[0] == "files"


def file_bytes(file_field) -> bytes:
    with file_field.open("rb") as f:
        return f.read()


def file_hash(file_field) -> str:
    if not file_field:
        return ""
    return sha256(file_bytes(file_field))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
