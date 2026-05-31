from django.core.management.base import BaseCommand, CommandError

from skoljka.apps.accounts.models import User
from skoljka.apps.sources.archive_transfer import (
    ImportOptions,
    apply_import,
    human_summary,
    plan_import,
    plan_json,
)


class Command(BaseCommand):
    help = "Dry-run or apply a Skoljka archive zip import."

    def add_arguments(self, parser):
        parser.add_argument("archive", help="Archive zip path.")
        parser.add_argument("--owner", required=True, help="Username for created sources/problems/documents.")
        parser.add_argument("--dry-run", action="store_true", default=False, help="No-op; dry run is the default.")
        parser.add_argument("--do-it", action="store_true", default=False, help="Apply the import.")
        parser.add_argument("--existing-problems", choices=["overwrite", "skip"])
        parser.add_argument("--document-conflicts", choices=["overwrite", "skip"])
        parser.add_argument("--attachment-conflicts", choices=["overwrite", "skip"])
        parser.add_argument("--missing-attachments", choices=["delete", "keep"])
        parser.add_argument("--ignore-missing-tags", action="store_true", default=False)
        parser.add_argument("--no-create-missing-tags", action="store_false", dest="create_missing_tags", default=True)
        parser.add_argument("--update-existing-tags", action="store_true", default=False)
        parser.add_argument("--public", action="store_true", default=False, dest="force_public")
        parser.add_argument("--private", action="store_true", default=False, dest="force_private")
        parser.add_argument("--json", action="store_true", default=False, dest="json_only")

    def handle(self, *args, **options):
        try:
            owner = User.objects.get(username=options["owner"])
        except User.DoesNotExist as exc:
            raise CommandError(f"Unknown owner user: {options['owner']}") from exc

        force_public = None
        if options["force_public"] and options["force_private"]:
            raise CommandError("Use only one of --public or --private.")
        if options["force_public"]:
            force_public = True
        elif options["force_private"]:
            force_public = False

        import_options = ImportOptions(
            owner=owner,
            do_it=options["do_it"],
            existing_problems=options["existing_problems"],
            document_conflicts=options["document_conflicts"],
            attachment_conflicts=options["attachment_conflicts"],
            missing_attachments=options["missing_attachments"],
            create_missing_tags=options["create_missing_tags"],
            update_existing_tags=options["update_existing_tags"],
            ignore_missing_tags=options["ignore_missing_tags"],
            force_public=force_public,
        )
        plan = plan_import(options["archive"], import_options)

        if options["do_it"] and not plan.can_apply:
            if options["json_only"]:
                self.stdout.write(plan_json(plan))
            raise CommandError("Import has unresolved conflicts or errors. Run without --do-it to inspect dry-run output.")

        if options["do_it"]:
            apply_import(options["archive"], import_options, plan)

        if options["json_only"]:
            self.stdout.write(plan_json(plan))
        else:
            self.stdout.write(human_summary(plan))
            self.stdout.write("")
            self.stdout.write(plan_json(plan))

