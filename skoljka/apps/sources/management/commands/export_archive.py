from django.core.management.base import BaseCommand, CommandError

from skoljka.apps.sources.archive_transfer import ExportOptions, export_archive
from skoljka.apps.sources.models import Source


class Command(BaseCommand):
    help = "Export sources, problems, documents, and attachments as a Skoljka archive zip."

    def add_arguments(self, parser):
        parser.add_argument("--source", action="append", dest="sources", required=True, help="Source slug to export. Can be repeated.")
        parser.add_argument("--output", required=True, help="Output zip path.")
        parser.add_argument("--include-children", action="store_true", default=True)
        parser.add_argument("--no-include-children", action="store_false", dest="include_children")
        parser.add_argument("--include-documents", action="store_true", default=True)
        parser.add_argument("--no-include-documents", action="store_false", dest="include_documents")
        parser.add_argument("--include-attachments", action="store_true", default=True)
        parser.add_argument("--no-include-attachments", action="store_false", dest="include_attachments")
        parser.add_argument("--public-only", action="store_true", default=False)

    def handle(self, *args, **options):
        source_slugs = options["sources"]
        missing = sorted(set(source_slugs) - set(Source.objects.filter(slug__in=source_slugs).values_list("slug", flat=True)))
        if missing:
            raise CommandError("Unknown source slug(s): " + ", ".join(missing))

        summary = export_archive(ExportOptions(
            source_slugs=source_slugs,
            output=options["output"],
            include_children=options["include_children"],
            include_documents=options["include_documents"],
            include_attachments=options["include_attachments"],
            public_only=options["public_only"],
        ))
        self.stdout.write(self.style.SUCCESS(f"Archive exported to {options['output']}"))
        for key, value in summary.items():
            self.stdout.write(f"{key}: {value}")

