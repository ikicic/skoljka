from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import UploadedFile
from django.db import models
from django.utils.text import get_valid_filename


def _attachment_upload_to(instance: "ContentAttachment", filename: str) -> str:
    return f"content/{instance.content_id}/attachments/{instance.name or filename}"


def _safe_attachment_name(name: str) -> str:
    name = get_valid_filename(name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1])
    return name or "attachment"


def _unique_attachment_name(content: "Content", requested: str) -> str:
    requested = _safe_attachment_name(requested)
    stem, dot, ext = requested.partition(".")
    if dot:
        base, suffix = stem, f".{ext}"
    else:
        base, suffix = requested, ""

    candidate = requested
    i = 2
    existing = set(content.attachments.values_list("name", flat=True))
    while candidate in existing:
        candidate = f"{base}-{i}{suffix}"
        i += 1
    return candidate


class Content(models.Model):
    id: int
    content_type_id: int
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    original_language = models.CharField(max_length=10, default="en")
    source_md = models.JSONField(default=dict)
    compiled_html = models.JSONField(default=dict, blank=True)
    search_text = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id"],
                name="unique_content_per_object",
            ),
        ]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def save(self, **kwargs: object) -> None:
        from skoljka.utils.markdown import compile_markdown

        compiled: dict[str, str] = {}
        search_parts: list[str] = []
        attachment_urls = self.attachment_url_map() if self.pk else None
        for lang, source in self.source_md.items():
            html, text = compile_markdown(source, attachment_urls=attachment_urls)
            compiled[lang] = html
            if text:
                search_parts.append(text)
        self.compiled_html = compiled
        self.search_text = " ".join(search_parts)
        super().save(**kwargs)

    def attachment_url_map(self) -> dict[str, str]:
        return {a.name: a.file.url for a in self.attachments.all() if a.file}

    def languages(self) -> list[str]:
        return list(self.source_md.keys())

    def source_for(self, language: str | None = None) -> str:
        lang = self.resolve_language(language)
        return self.source_md.get(lang, "") if lang else ""

    def html_for(self, language: str | None = None) -> str:
        lang = self.resolve_language(language)
        return self.compiled_html.get(lang, "") if lang else ""

    def resolve_language(self, language: str | None = None) -> str:
        if language and language in self.source_md:
            return language
        if self.original_language in self.source_md:
            return self.original_language
        return next(iter(self.source_md), "")

    def set_text(self, language: str, source: str) -> None:
        texts = dict(self.source_md)
        language = language.strip() or self.original_language or "en"
        if source.strip():
            texts[language] = source
        else:
            texts.pop(language, None)
        self.source_md = texts

    def __str__(self) -> str:
        return f"Content({self.content_type}, {self.object_id})"


class ContentVersion(models.Model):
    id: int
    content_id: int
    content = models.ForeignKey(
        Content, on_delete=models.CASCADE, related_name="versions"
    )
    source_md = models.JSONField(default=dict)
    edited_by_id: int | None
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    edited_at = models.DateTimeField(auto_now_add=True)
    edit_summary = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-edited_at"]

    def __str__(self) -> str:
        return f"ContentVersion({self.content_id}, {self.edited_at})"


class ContentAttachment(models.Model):
    id: int
    content_id: int
    content = models.ForeignKey(
        Content, on_delete=models.CASCADE, related_name="attachments"
    )
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to=_attachment_upload_to)
    mime_type = models.CharField(max_length=100, blank=True)
    size = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["content", "name"],
                name="unique_attachment_name_per_content",
            ),
        ]

    def __str__(self) -> str:
        return f"ContentAttachment({self.content_id}, {self.name})"

    @classmethod
    def from_upload(
        cls,
        content: Content,
        upload: UploadedFile,
        *,
        name: str | None = None,
    ) -> "ContentAttachment":
        attachment_name = _unique_attachment_name(content, name or upload.name)
        return cls.objects.create(
            content=content,
            name=attachment_name,
            file=upload,
            mime_type=getattr(upload, "content_type", "") or "",
            size=upload.size,
        )
