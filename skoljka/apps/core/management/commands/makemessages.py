import os

from django.core.management.commands.makemessages import BuildFile
from django.core.management.commands.makemessages import Command as DjangoMakeMessagesCommand
from django.utils.functional import cached_property


class PythonJsxBuildFile(BuildFile):
    @cached_property
    def is_templatized(self):
        if os.path.splitext(self.translatable.file)[1] == ".px":
            return False
        return super().is_templatized


class Command(DjangoMakeMessagesCommand):
    build_file_class = PythonJsxBuildFile

    def handle(self, *args, **options):
        if options["domain"] == "django" and options["extensions"] is None:
            options["extensions"] = ["html", "txt", "py", "px"]
        if options["domain"] == "django":
            self.xgettext_options = self.xgettext_options[:] + [
                "--keyword=_t",
                "--keyword=ngettext:1,2",
            ]
        return super().handle(*args, **options)
