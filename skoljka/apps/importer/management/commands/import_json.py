"""Import problems from a JSON file.

Expected JSON format:
{
    "sources": [
        {
            "slug": "imo",
            "translations": {"en": {"name": "IMO", "description": "..."}},
            "parent_slug": null,
            "tags": ["international"]
        }
    ],
    "tags": [
        {
            "slug": "algebra",
            "kind": "topic",
            "translations": {"en": "Algebra"},
            "short_translations": {"en": "Alg"},
            "descriptions": {"en": "Algebraic equations, expressions, functions, or inequalities."}
        },
        {"slug": "international", "kind": "meta", "translations": {"en": "International"}}
    ],
    "problems": [
        {
            "source_slug": "imo",
            "year": 2024,
            "problem_label": "1",
            "tags": ["algebra"],
            "statements": {
                "en": "Let $n$ be a positive integer..."
            }
        }
    ]
}

Problems are keyed by (source, year, problem_label); importing the same tuple
again updates the existing problem. Problems without a full natural key are
always created anew.
"""

import json
from pathlib import Path
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from skoljka.apps.content.models import Content
from skoljka.apps.problems.models import Problem
from skoljka.apps.sources.models import Source
from skoljka.apps.tags.models import Tag


class Command(BaseCommand):
    help = "Import problems, sources, and tags from a JSON file."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("file", type=Path)

    def handle(self, *args: Any, **options: Any) -> None:
        data = json.loads(options["file"].read_text())

        tags_data = data.get("tags", [])
        sources_data = data.get("sources", [])
        problems_data = data.get("problems", [])

        self._warn_duplicate_short_translations(tags_data)

        # Import tags.
        for t in tags_data:
            tag, created = Tag.objects.update_or_create(
                slug=t["slug"],
                defaults={
                    "kind": t.get("kind", "topic"),
                    "hidden": t.get("hidden", False),
                    "translations": t.get("translations", {}),
                    "short_translations": t.get("short_translations", {}),
                    "descriptions": t.get("descriptions", {}),
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action} tag: {tag.slug}")

        # Set tag parents (second pass).
        for t in tags_data:
            parent_slug = t.get("parent_slug")
            if parent_slug:
                tag = Tag.objects.get(slug=t["slug"])
                tag.parent = Tag.objects.get(slug=parent_slug)
                tag.save()

        # Import sources.
        for s in sources_data:
            source, created = Source.objects.update_or_create(
                slug=s["slug"],
                defaults={
                    "translations": s.get("translations", {}),
                    "order": s.get("order", 0),
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action} source: {source.slug}")

        # Set source parents and tags (second pass).
        for s in sources_data:
            source = Source.objects.get(slug=s["slug"])
            parent_slug = s.get("parent_slug")
            if parent_slug:
                source.parent = Source.objects.get(slug=parent_slug)
                source.save()
            tag_slugs = s.get("tags", [])
            if tag_slugs:
                source.tags.set(Tag.objects.filter(slug__in=tag_slugs))

        # Import problems.
        problem_ct = ContentType.objects.get_for_model(Problem)
        for p in problems_data:
            source = None
            if p.get("source_slug"):
                source = Source.objects.get(slug=p["source_slug"])

            year = p.get("year")
            problem_label = str(p.get("problem_label") or p.get("problem_number") or "").strip()
            defaults = {
                "title": p.get("title", ""),
                "expected_answer": p.get("expected_answer"),
            }
            if source and year and problem_label:
                problem, created = Problem.objects.update_or_create(
                    source=source,
                    year=year,
                    problem_label=problem_label,
                    defaults=defaults,
                )
            else:
                problem = Problem.objects.create(
                    source=source,
                    year=year,
                    problem_label=problem_label,
                    **defaults,
                )
                created = True
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action} problem: {problem.display_title} (id={problem.id})")

            # Tags.
            tag_slugs = p.get("tags", [])
            if tag_slugs:
                problem.tags.set(Tag.objects.filter(slug__in=tag_slugs))

            # Statements (Content).
            for lang, text in p.get("statements", {}).items():
                content, _ = Content.objects.get_or_create(
                    content_type=problem_ct,
                    object_id=problem.id,
                    defaults={"original_language": p.get("original_language", lang), "source_md": {}},
                )
                content.set_text(lang, text)
                if not content.original_language:
                    content.original_language = lang
                content.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(tags_data)} tags, {len(sources_data)} sources, "
                f"{len(problems_data)} problems."
            )
        )

    def _warn_duplicate_short_translations(self, tags_data: list[dict[str, Any]]) -> None:
        by_language_and_name: dict[tuple[str, str], list[str]] = {}
        for tag in tags_data:
            slug = tag.get("slug")
            short_translations = tag.get("short_translations") or {}
            if not isinstance(slug, str) or not isinstance(short_translations, dict):
                continue
            for language, name in short_translations.items():
                if not isinstance(language, str) or not isinstance(name, str):
                    continue
                normalized = name.strip().casefold()
                if not normalized:
                    continue
                by_language_and_name.setdefault((language, normalized), []).append(slug)

        for (language, _normalized_name), slugs in sorted(by_language_and_name.items()):
            if len(slugs) <= 1:
                continue
            display_name = next(
                tag.get("short_translations", {}).get(language, "")
                for tag in tags_data
                if tag.get("slug") == slugs[0]
            )
            self.stderr.write(
                self.style.WARNING(
                    f"Warning: duplicate short translation {language!r}={display_name!r} "
                    f"for tags: {', '.join(slugs)}"
                )
            )
