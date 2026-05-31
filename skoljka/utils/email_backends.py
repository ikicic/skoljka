import sys

from django.core.mail.backends.base import BaseEmailBackend


class PlainConsoleEmailBackend(BaseEmailBackend):
    """Development backend that prints decoded email bodies instead of raw MIME."""

    def __init__(self, *args, stream=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.stream = stream or sys.stdout

    def send_messages(self, email_messages):
        count = 0
        for message in email_messages:
            self._write_message(message)
            count += 1
        return count

    def _write_message(self, message):
        self.stream.write("-" * 79 + "\n")
        self.stream.write(f"Subject: {message.subject}\n")
        self.stream.write(f"From: {message.from_email}\n")
        self.stream.write(f"To: {', '.join(message.recipients())}\n")
        self.stream.write("\n")
        self.stream.write(message.body or "")
        if message.body and not message.body.endswith("\n"):
            self.stream.write("\n")
        for content, mimetype in getattr(message, "alternatives", []):
            self.stream.write(f"\n[{mimetype}]\n")
            self.stream.write(content)
            if content and not content.endswith("\n"):
                self.stream.write("\n")
        self.stream.write("-" * 79 + "\n")
        self.stream.flush()
