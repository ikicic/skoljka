from django import forms
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from skoljka.apps.content.models import Content
from skoljka.apps.news.models import NewsPost


class NewsPostForm(forms.Form):
    title = forms.CharField(
        max_length=255,
        label=_("Title"),
        error_messages={"required": _("Title is required.")},
    )
    slug = forms.SlugField(
        required=False,
        label=_("Slug"),
        help_text=_("Generated from title if empty"),
    )
    language = forms.CharField(initial="en", max_length=16, label=_("Language"))
    content_md = forms.CharField(
        required=False,
        widget=forms.Textarea,
        label=_("Content"),
    )
    hidden = forms.BooleanField(required=False, initial=True, label=_("Hidden"))

    def __init__(self, *args, user, instance: NewsPost | None = None, **kwargs):
        self.user = user
        self.instance = instance
        super().__init__(*args, **kwargs)

    def clean_slug(self):
        title = self.cleaned_data.get("title", "")
        slug = slugify(self.cleaned_data.get("slug") or title)
        if not slug:
            raise forms.ValidationError(_("Slug is required."))
        qs = NewsPost.objects.filter(slug=slug)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_("Slug is already taken."))
        return slug

    def save(self) -> NewsPost:
        post = self.instance or NewsPost(created_by=self.user)
        post.title = self.cleaned_data["title"]
        post.slug = self.cleaned_data["slug"]
        post.hidden = self.cleaned_data["hidden"]
        post.save()

        language = self.cleaned_data["language"] or "en"
        source_md = self.cleaned_data["content_md"]
        content = post.content.first()
        if source_md.strip():
            if content is None:
                content = Content(content_object=post, original_language=language, source_md={})
            content.set_text(language, source_md)
            content.original_language = language
            content.save()
        elif content is not None:
            content.set_text(language, "")
            if content.attachments.exists():
                content.save()
            else:
                content.delete()

        return post

    @classmethod
    def initial_for(cls, post: NewsPost | None) -> dict:
        if post is None:
            return {"hidden": True}
        content = post.content.first()
        language = content.resolve_language() if content else "en"
        return {
            "title": post.title,
            "slug": post.slug,
            "language": language,
            "content_md": content.source_for(language) if content else "",
            "hidden": post.hidden,
        }
