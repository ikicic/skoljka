from __future__ import annotations

import json
import zipfile
from pathlib import PurePosixPath
from typing import Any

from django.core.files.base import ContentFile
from django.db import transaction

from skoljka.apps.content.models import Content, ContentAttachment
from skoljka.apps.problems.models import Problem
from skoljka.apps.sources.archive_paths import (
    attachment_archive_path,
    document_key,
    file_bytes,
    file_hash,
    problem_key,
    safe_zip_path,
    sha256,
    source_document_archive_path,
)
from skoljka.apps.sources.archive_types import (
    SCHEMA,
    ExportOptions,
    ImportOptions,
    ImportPlan,
    PlannedChange,
)
from skoljka.apps.sources.models import Source, SourceDocument
from skoljka.apps.tags.models import Tag

Payload = dict[str, Any]
FileField = Any


def export_archive(options: ExportOptions) -> dict[str, int]:
    sources = _export_sources(options)
    problems = list(
        Problem.objects.filter(source__in=sources)
        .select_related("source")
        .prefetch_related("tags", "content__attachments")
        .order_by("source__slug", "year", "problem_label", "id")
    )
    if options.public_only:
        problems = [p for p in problems if p.is_public]

    used_tags = set()
    for source in sources:
        used_tags.update(source.tags.values_list("slug", flat=True))
    for problem in problems:
        used_tags.update(problem.tags.values_list("slug", flat=True))
    tags = list(Tag.objects.filter(slug__in=used_tags).order_by("slug"))

    source_docs = []
    if options.include_documents:
        source_docs = list(SourceDocument.objects.filter(source__in=sources))

    with zipfile.ZipFile(options.output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        _write_json(zf, "manifest.json", {"schema": SCHEMA})
        _write_json(zf, "sources.json", [_source_payload(s) for s in sources])
        _write_json(zf, "tags.json", [_tag_payload(t) for t in tags])
        _write_json(zf, "problems.json", [_problem_payload(zf, p, options) for p in problems])
        _write_json(zf, "source_documents.json", [_source_document_payload(zf, d) for d in source_docs])

    return {
        "sources": len(sources),
        "tags": len(tags),
        "problems": len(problems),
        "source_documents": len(source_docs),
    }


def plan_import(zip_path: str, options: ImportOptions) -> ImportPlan:
    archive = _Archive(zip_path)
    plan = ImportPlan(
        schema="",
        mode="apply" if options.do_it else "dry_run",
        policies=_policy_dict(options),
    )
    try:
        archive.load()
    except ValueError as exc:
        plan.errors.append(_error("archive", {}, str(exc)))
        return plan

    plan.schema = archive.manifest.get("schema", "")
    if plan.schema != SCHEMA:
        plan.errors.append(_error("archive", {}, f"Unsupported schema: {plan.schema}"))
        return plan

    _validate_archive(archive, plan)
    if plan.errors:
        return plan

    _plan_tags(archive, options, plan)
    _plan_sources(archive, options, plan)
    _plan_problems(archive, options, plan)
    _plan_source_documents(archive, options, plan)
    return plan


def apply_import(zip_path: str, options: ImportOptions, plan: ImportPlan | None = None) -> ImportPlan:
    if not options.do_it:
        raise ValueError("apply_import requires options.do_it=True")
    plan = plan or plan_import(zip_path, options)
    if not plan.can_apply:
        raise ValueError("Cannot apply import with unresolved conflicts or errors")

    archive = _Archive(zip_path)
    archive.load()
    written_files: list[FileField] = []
    try:
        with transaction.atomic():
            tags_by_slug = _apply_tags(archive, options)
            sources_by_key = _apply_sources(archive, options, tags_by_slug)
            problems_by_key = _apply_problems(archive, options, sources_by_key, tags_by_slug, written_files)
            _apply_source_documents(archive, options, sources_by_key, written_files)
            _apply_attachment_deletions(archive, options, problems_by_key)
    except Exception:
        for file_field in written_files:
            try:
                file_field.delete(save=False)
            except Exception:
                pass
        raise
    return plan


def human_summary(plan: ImportPlan) -> str:
    lines = [
        f"Archive schema: {plan.schema or '(unknown)'}",
        f"Mode: {plan.mode}",
        f"Can apply: {'yes' if plan.can_apply else 'no'}",
        "",
    ]
    summary = plan.summary()
    for section in ("create", "update", "skip", "overwrite", "delete", "keep"):
        values = summary.get(section, {})
        if values:
            lines.append(f"{section.title()}:")
            for key, value in sorted(values.items()):
                lines.append(f"  {key}: {value}")
            lines.append("")
    lines.append(f"Conflicts: {summary['conflicts']}")
    lines.append(f"Unaddressed conflicts: {summary['unaddressed_conflicts']}")
    lines.append(f"Errors: {summary['errors']}")
    if plan.conflicts:
        lines.extend(["", "Conflict details:"])
        for conflict in plan.conflicts:
            selected = conflict.selected_action or "unaddressed"
            lines.append(f"  {conflict.object_type} {conflict.identity}: {selected} ({conflict.reason})")
    if plan.errors:
        lines.extend(["", "Errors:"])
        for error in plan.errors:
            lines.append(f"  {error.object_type} {error.identity}: {error.reason}")
    return "\n".join(lines)


def plan_json(plan: ImportPlan) -> str:
    return json.dumps(plan.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


class _Archive:
    def __init__(self, path: str):
        self.path = path
        self.manifest: Payload = {}
        self.sources: list[Payload] = []
        self.tags: list[Payload] = []
        self.problems: list[Payload] = []
        self.source_documents: list[Payload] = []

    def load(self) -> None:
        try:
            with zipfile.ZipFile(self.path) as zf:
                self.manifest = _read_json(zf, "manifest.json")
                self.sources = _read_json(zf, "sources.json")
                self.tags = _read_json(zf, "tags.json")
                self.problems = _read_json(zf, "problems.json")
                self.source_documents = _read_json(zf, "source_documents.json")
        except (KeyError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
            raise ValueError(str(exc)) from exc

    def file_bytes(self, path: str) -> bytes:
        with zipfile.ZipFile(self.path) as zf:
            return zf.read(path)


def _export_sources(options: ExportOptions) -> list[Source]:
    selected = list(Source.objects.filter(slug__in=options.source_slugs).order_by("order", "slug"))
    if not options.include_children:
        return selected
    result: list[Source] = []
    seen: set[int] = set()
    stack = list(selected)
    while stack:
        source = stack.pop(0)
        if source.pk in seen:
            continue
        seen.add(source.pk)
        result.append(source)
        stack.extend(list(Source.objects.filter(parent=source).order_by("order", "slug")))
    if options.public_only:
        result = [s for s in result if s.is_public]
    return result


def _source_payload(source: Source) -> Payload:
    return {
        "key": source.slug,
        "slug": source.slug,
        "parent": source.parent.slug if source.parent else None,
        "order": source.order,
        "is_public": source.is_public,
        "translations": source.translations,
        "tags": list(source.tags.order_by("slug").values_list("slug", flat=True)),
    }


def _tag_payload(tag: Tag) -> Payload:
    return {
        "slug": tag.slug,
        "kind": tag.kind,
        "hidden": tag.hidden,
        "translations": tag.translations,
        "short_translations": tag.short_translations,
        "descriptions": tag.descriptions,
    }


def _problem_payload(zf: zipfile.ZipFile, problem: Problem, options: ExportOptions) -> Payload:
    content = problem.content.first()
    key = problem_key(problem)
    payload = {
        "key": key,
        "source": problem.source.slug if problem.source else None,
        "year": problem.year,
        "problem_label": problem.problem_label,
        "title": problem.title,
        "is_public": problem.is_public,
        "tags": list(problem.tags.order_by("slug").values_list("slug", flat=True)),
        "content": None,
    }
    if content:
        attachments = []
        if options.include_attachments:
            for attachment in content.attachments.all():
                path = attachment_archive_path(problem, attachment.name)
                data = file_bytes(attachment.file)
                zf.writestr(path, data)
                attachments.append({
                    "name": attachment.name,
                    "path": path,
                    "content_type": attachment.mime_type,
                    "size": len(data),
                    "sha256": sha256(data),
                })
        payload["content"] = {
            "original_language": content.original_language,
            "source_md": content.source_md,
            "attachments": attachments,
        }
    return payload


def _source_document_payload(zf: zipfile.ZipFile, document: SourceDocument) -> Payload:
    filename = document.original_filename or PurePosixPath(document.file.name).name
    path = source_document_archive_path(document.source.slug, document.year, document.kind, filename)
    data = file_bytes(document.file)
    zf.writestr(path, data)
    return {
        "key": document_key(document.source.slug, document.year, document.kind, filename),
        "source": document.source.slug,
        "year": document.year,
        "language": document.language,
        "kind": document.kind,
        "title": document.title,
        "original_filename": filename,
        "path": path,
        "size": len(data),
        "sha256": sha256(data),
    }


def _write_json(zf: zipfile.ZipFile, name: str, data: Any) -> None:
    zf.writestr(name, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def _read_json(zf: zipfile.ZipFile, name: str) -> Any:
    return json.loads(zf.read(name).decode("utf-8"))


def _validate_archive(archive: _Archive, plan: ImportPlan) -> None:
    _validate_unique([s.get("slug") for s in archive.sources], "source", "slug", plan)
    _validate_unique([s.get("key") for s in archive.sources], "source", "key", plan)
    _validate_unique([t.get("slug") for t in archive.tags], "tag", "slug", plan)
    _validate_unique([p.get("key") for p in archive.problems], "problem", "key", plan)
    tuples = [
        (p.get("source"), p.get("year"), _payload_problem_label(p))
        for p in archive.problems
        if p.get("source") and p.get("year") is not None and _payload_problem_label(p)
    ]
    _validate_unique(tuples, "problem", "(source, year, problem_label)", plan)

    source_keys = {s.get("key") for s in archive.sources}
    source_slugs = {s.get("slug") for s in archive.sources}
    db_sources = set(Source.objects.filter(slug__in=source_keys | source_slugs).values_list("slug", flat=True))
    for source in archive.sources:
        parent = source.get("parent")
        if parent and parent not in source_keys and parent not in db_sources:
            plan.errors.append(_error("source", {"slug": source.get("slug")}, f"Missing parent source {parent}"))
    for problem in archive.problems:
        source = problem.get("source")
        if source and source not in source_keys and source not in db_sources:
            plan.errors.append(_error("problem", {"key": problem.get("key")}, f"Missing source {source}"))
    for document in archive.source_documents:
        source = document.get("source")
        if source and source not in source_keys and source not in db_sources:
            plan.errors.append(_error("source_document", {"key": document.get("key")}, f"Missing source {source}"))

    with zipfile.ZipFile(archive.path) as zf:
        names = set(zf.namelist())
        for entry in _file_entries(archive):
            path = entry.get("path", "")
            if not safe_zip_path(path):
                plan.errors.append(_error("file", {"path": path}, "Unsafe file path"))
                continue
            if path not in names:
                plan.errors.append(_error("file", {"path": path}, "Missing file in zip"))
                continue
            data = zf.read(path)
            if entry.get("size") != len(data):
                plan.errors.append(_error("file", {"path": path}, "File size mismatch"))
            if entry.get("sha256") != sha256(data):
                plan.errors.append(_error("file", {"path": path}, "SHA-256 mismatch"))


def _validate_unique(values: list[Any], object_type: str, field_name: str, plan: ImportPlan) -> None:
    seen = set()
    for value in values:
        if value in seen:
            plan.errors.append(_error(object_type, {field_name: value}, f"Duplicate {field_name} in archive"))
        seen.add(value)


def _file_entries(archive: _Archive):
    for problem in archive.problems:
        content = problem.get("content") or {}
        for attachment in content.get("attachments") or []:
            yield attachment
    yield from archive.source_documents


def _plan_tags(archive: _Archive, options: ImportOptions, plan: ImportPlan) -> None:
    archive_tags = {slug: t for t in archive.tags if (slug := _payload_str(t, "slug"))}
    referenced = _referenced_tags(archive)
    existing = set(Tag.objects.filter(slug__in=referenced).values_list("slug", flat=True))
    for slug in sorted(referenced):
        if slug in existing:
            plan.changes.append(PlannedChange("tag", {"slug": slug}, "skip", "existing tag preserved"))
        elif slug in archive_tags and options.create_missing_tags:
            plan.changes.append(PlannedChange("tag", {"slug": slug}, "create"))
        elif options.ignore_missing_tags:
            plan.changes.append(PlannedChange("tag", {"slug": slug}, "skip", "missing tag ignored"))
        else:
            plan.errors.append(_error("tag", {"slug": slug}, "Missing tag"))


def _plan_sources(archive: _Archive, options: ImportOptions, plan: ImportPlan) -> None:
    existing = {s.slug: s for s in Source.objects.filter(slug__in=[_payload_str(s, "slug") for s in archive.sources])}
    for payload in archive.sources:
        slug = _payload_str(payload, "slug")
        source = existing.get(slug)
        if source:
            action = "update" if _source_differs(source, payload, options) else "skip"
            plan.changes.append(PlannedChange("source", {"slug": slug}, action))
        else:
            plan.changes.append(PlannedChange("source", {"slug": slug}, "create"))


def _plan_problems(archive: _Archive, options: ImportOptions, plan: ImportPlan) -> None:
    sources = _source_lookup_for_plan(archive)
    tags_by_slug = {t.slug: t for t in Tag.objects.filter(slug__in=_referenced_tags(archive))}
    for payload in archive.problems:
        problem = _find_problem(payload, sources)
        identity = _problem_identity(payload)
        if not problem:
            plan.changes.append(PlannedChange("problem", identity, "create"))
            continue
        differs = _problem_differs(problem, payload, tags_by_slug)
        if not differs:
            plan.changes.append(PlannedChange("problem", identity, "skip", "identical"))
        elif options.existing_problems:
            plan.changes.append(PlannedChange(
                "problem",
                identity,
                "conflict",
                "existing problem differs",
                available_actions=["overwrite", "skip"],
                selected_action=options.existing_problems,
            ))
        else:
            plan.changes.append(PlannedChange(
                "problem",
                identity,
                "conflict",
                "existing problem differs",
                available_actions=["overwrite", "skip"],
            ))
        if differs and options.existing_problems != "skip":
            _plan_problem_attachments(problem, payload, options, plan)


def _plan_problem_attachments(problem: Problem, payload: Payload, options: ImportOptions, plan: ImportPlan) -> None:
    content = problem.content.first()
    existing = {a.name: a for a in content.attachments.all()} if content else {}
    incoming = {
        a.get("name"): a
        for a in ((payload.get("content") or {}).get("attachments") or [])
    }
    for name, attachment in incoming.items():
        current = existing.get(name)
        if current and file_hash(current.file) != attachment.get("sha256"):
            plan.changes.append(PlannedChange(
                "content_attachment",
                {**_problem_identity(payload), "name": name},
                "conflict",
                "attachment with same name has different hash",
                available_actions=["overwrite", "skip"],
                selected_action=options.attachment_conflicts,
            ))
    for name in sorted(set(existing) - set(incoming)):
        plan.changes.append(PlannedChange(
            "content_attachment",
            {**_problem_identity(payload), "name": name},
            "conflict",
            "existing attachment is missing from archive",
            available_actions=["delete", "keep"],
            selected_action=options.missing_attachments,
        ))


def _plan_source_documents(archive: _Archive, options: ImportOptions, plan: ImportPlan) -> None:
    sources = _source_lookup_for_plan(archive)
    for payload in archive.source_documents:
        source = sources.get(_payload_str(payload, "source"))
        existing = None
        if source:
            existing = SourceDocument.objects.filter(
                source=source,
                year=payload.get("year"),
                kind=payload.get("kind") or SourceDocument.Kind.PROBLEMS,
                original_filename=payload.get("original_filename") or "",
            ).first()
        identity = _document_identity(payload)
        if not existing:
            plan.changes.append(PlannedChange("source_document", identity, "create"))
        elif file_hash(existing.file) == payload.get("sha256"):
            plan.changes.append(PlannedChange("source_document", identity, "skip", "identical"))
        else:
            plan.changes.append(PlannedChange(
                "source_document",
                identity,
                "conflict",
                "document with same identity has different hash",
                available_actions=["overwrite", "skip"],
                selected_action=options.document_conflicts,
            ))


def _apply_tags(archive: _Archive, options: ImportOptions) -> dict[str, Tag]:
    result = {t.slug: t for t in Tag.objects.filter(slug__in=_referenced_tags(archive))}
    archive_tags = {slug: t for t in archive.tags if (slug := _payload_str(t, "slug"))}
    for slug in sorted(_referenced_tags(archive)):
        if slug in result:
            continue
        payload = archive_tags.get(slug)
        if not payload:
            if options.ignore_missing_tags:
                continue
            raise ValueError(f"Missing tag {slug}")
        result[slug] = Tag.objects.create(
            slug=slug,
            kind=payload.get("kind") or Tag.Kind.TOPIC,
            hidden=bool(payload.get("hidden", False)),
            translations=payload.get("translations") or {},
            short_translations=payload.get("short_translations") or {},
            descriptions=payload.get("descriptions") or {},
        )
    return result


def _apply_sources(archive: _Archive, options: ImportOptions, tags_by_slug: dict[str, Tag]) -> dict[str, Source]:
    by_key: dict[str, Source] = {}
    pending = list(archive.sources)
    while pending:
        progressed = False
        for payload in list(pending):
            parent_key = _payload_str(payload, "parent")
            parent = by_key.get(parent_key) or Source.objects.filter(slug=parent_key).first() if parent_key else None
            if parent_key and not parent:
                continue
            slug = _payload_str(payload, "slug")
            key = _payload_str(payload, "key") or slug
            source, created = Source.objects.get_or_create(
                slug=slug,
                defaults={"created_by": options.owner},
            )
            source.parent_id = parent.pk if parent else None
            source.order = int(payload.get("order") or 0)
            source.is_public = options.force_public if options.force_public is not None else bool(payload.get("is_public", True))
            source.translations = payload.get("translations") or {}
            if created:
                source.created_by = options.owner
            source.save()
            source.tags.set([tags_by_slug[s] for s in payload.get("tags") or [] if s in tags_by_slug])
            by_key[key] = source
            by_key[slug] = source
            pending.remove(payload)
            progressed = True
        if not progressed:
            raise ValueError("Cannot resolve source parents")
    return by_key


def _apply_problems(archive: _Archive, options: ImportOptions, sources_by_key: dict[str, Source], tags_by_slug: dict[str, Tag], written_files: list[FileField]) -> dict[str, Problem]:
    result: dict[str, Problem] = {}
    for payload in archive.problems:
        problem = _find_problem(payload, sources_by_key)
        key = _payload_str(payload, "key")
        if problem and options.existing_problems == "skip":
            result[key] = problem
            continue
        if not problem:
            problem = Problem(created_by=options.owner)
        problem.source = sources_by_key.get(_payload_str(payload, "source"))
        problem.year = payload.get("year")
        problem.problem_label = _payload_problem_label(payload)
        problem.title = payload.get("title") or ""
        problem.is_public = options.force_public if options.force_public is not None else bool(payload.get("is_public", True))
        problem.save()
        problem.tags.set([tags_by_slug[s] for s in payload.get("tags") or [] if s in tags_by_slug])
        _apply_problem_content(archive, problem, payload, options, written_files)
        result[key] = problem
    return result


def _apply_problem_content(archive: _Archive, problem: Problem, payload: Payload, options: ImportOptions, written_files: list[FileField]) -> None:
    content_payload = payload.get("content")
    existing = problem.content.first()
    if not content_payload:
        if existing:
            existing.delete()
        return
    content = existing or Content(content_object=problem)
    content.source_md = content_payload.get("source_md") or {}
    content.original_language = content_payload.get("original_language") or next(iter(content.source_md), "en")
    content.save()

    incoming = {_payload_str(a, "name"): a for a in content_payload.get("attachments") or []}
    existing_attachments = {a.name: a for a in ContentAttachment.objects.filter(content=content)}
    attachments_changed = False
    for name, payload_attachment in incoming.items():
        current = existing_attachments.get(name)
        data = archive.file_bytes(_payload_str(payload_attachment, "path"))
        if current:
            same = file_hash(current.file) == payload_attachment.get("sha256")
            if same or options.attachment_conflicts == "skip":
                continue
            current.file.delete(save=False)
            current.file.save(name, ContentFile(data), save=False)
            written_files.append(current.file)
            current.mime_type = payload_attachment.get("content_type") or ""
            current.size = len(data)
            current.save()
            attachments_changed = True
        else:
            attachment = ContentAttachment(
                content=content,
                name=name,
                mime_type=payload_attachment.get("content_type") or "",
                size=len(data),
            )
            attachment.file.save(name, ContentFile(data), save=False)
            written_files.append(attachment.file)
            attachment.save()
            attachments_changed = True
    if options.missing_attachments == "delete":
        for name, attachment in existing_attachments.items():
            if name not in incoming:
                attachment.file.delete(save=False)
                attachment.delete()
                attachments_changed = True
    if attachments_changed:
        content.save()


def _apply_source_documents(archive: _Archive, options: ImportOptions, sources_by_key: dict[str, Source], written_files: list[FileField]) -> None:
    for payload in archive.source_documents:
        source = sources_by_key.get(_payload_str(payload, "source"))
        if not source:
            raise ValueError(f"Missing source {payload.get('source')}")
        existing = SourceDocument.objects.filter(
            source=source,
            year=payload.get("year"),
            kind=payload.get("kind") or SourceDocument.Kind.PROBLEMS,
            original_filename=payload.get("original_filename") or "",
        ).first()
        if existing:
            if file_hash(existing.file) == payload.get("sha256") or options.document_conflicts == "skip":
                continue
            document = existing
            document.file.delete(save=False)
        else:
            document = SourceDocument(source=source, uploaded_by=options.owner)
        path = _payload_str(payload, "path")
        data = archive.file_bytes(path)
        document.year = payload.get("year")
        document.language = payload.get("language") or ""
        document.kind = payload.get("kind") or SourceDocument.Kind.PROBLEMS
        document.title = payload.get("title") or ""
        document.original_filename = payload.get("original_filename") or PurePosixPath(path).name
        document.file.save(document.original_filename, ContentFile(data), save=False)
        written_files.append(document.file)
        document.save()


def _apply_attachment_deletions(archive: _Archive, options: ImportOptions, problems_by_key: dict[str, Problem]) -> None:
    # Attachment deletions are handled while applying each problem, after the
    # incoming attachment set is known. This hook keeps the apply pipeline
    # explicit and leaves room for future per-item GUI decisions.
    return None


def _referenced_tags(archive: _Archive) -> set[str]:
    tags = set()
    for source in archive.sources:
        tags.update(source.get("tags") or [])
    for problem in archive.problems:
        tags.update(problem.get("tags") or [])
    return tags


def _source_lookup_for_plan(archive: _Archive) -> dict[str, Source]:
    keys = {_payload_str(s, "slug") for s in archive.sources} | {_payload_str(s, "key") for s in archive.sources}
    existing = {s.slug: s for s in Source.objects.filter(slug__in=keys)}
    for payload in archive.sources:
        key = _payload_str(payload, "key")
        source = existing.get(_payload_str(payload, "slug"))
        if source:
            existing[key] = source
    return existing


def _source_differs(source: Source, payload: Payload, options: ImportOptions) -> bool:
    public = options.force_public if options.force_public is not None else bool(payload.get("is_public", True))
    return (
        source.order != int(payload.get("order") or 0)
        or source.is_public != public
        or source.translations != (payload.get("translations") or {})
        or sorted(source.tags.values_list("slug", flat=True)) != sorted(payload.get("tags") or [])
        or (source.parent.slug if source.parent else None) != payload.get("parent")
    )


def _find_problem(payload: Payload, sources_by_key: dict[str, Source]) -> Problem | None:
    source = sources_by_key.get(_payload_str(payload, "source"))
    problem_label = _payload_problem_label(payload)
    if source and payload.get("year") is not None and problem_label:
        return Problem.objects.filter(
            source=source,
            year=payload.get("year"),
            problem_label=problem_label,
        ).first()
    return None


def _problem_differs(problem: Problem, payload: Payload, tags_by_slug: dict[str, Tag]) -> bool:
    content_payload = payload.get("content") or {}
    content = problem.content.first()
    expected_tags = sorted([s for s in payload.get("tags") or [] if s in tags_by_slug])
    actual_tags = sorted(problem.tags.values_list("slug", flat=True))
    if problem.title != (payload.get("title") or ""):
        return True
    if problem.is_public != bool(payload.get("is_public", True)):
        return True
    if actual_tags != expected_tags:
        return True
    if bool(content) != bool(payload.get("content")):
        return True
    if content and content_payload:
        if content.original_language != (content_payload.get("original_language") or ""):
            return True
        if content.source_md != (content_payload.get("source_md") or {}):
            return True
        incoming = {a.get("name"): a.get("sha256") for a in content_payload.get("attachments") or []}
        existing = {a.name: file_hash(a.file) for a in content.attachments.all()}
        if incoming != existing:
            return True
    return False


def _problem_identity(payload: Payload) -> Payload:
    return {
        "source": payload.get("source"),
        "year": payload.get("year"),
        "problem_label": _payload_problem_label(payload),
        "key": payload.get("key"),
    }


def _payload_problem_label(payload: Payload) -> str:
    return str(payload.get("problem_label") or payload.get("problem_number") or "").strip()


def _payload_str(payload: Payload, key: str) -> str:
    return str(payload.get(key) or "").strip()


def _document_identity(payload: Payload) -> Payload:
    return {
        "source": payload.get("source"),
        "year": payload.get("year"),
        "kind": payload.get("kind"),
        "original_filename": payload.get("original_filename"),
    }


def _policy_dict(options: ImportOptions) -> Payload:
    return {
        "existing_problems": options.existing_problems,
        "document_conflicts": options.document_conflicts,
        "attachment_conflicts": options.attachment_conflicts,
        "missing_attachments": options.missing_attachments,
        "create_missing_tags": options.create_missing_tags,
        "update_existing_tags": options.update_existing_tags,
        "ignore_missing_tags": options.ignore_missing_tags,
        "force_public": options.force_public,
        "owner": options.owner.username,
    }


def _error(object_type: str, identity: Payload, reason: str) -> PlannedChange:
    return PlannedChange(object_type, identity, "conflict", reason)
