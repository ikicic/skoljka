from django import forms
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from skoljka.apps.content.models import Content, ContentAttachment
from skoljka.apps.problems.models import Problem
from skoljka.apps.sources.models import Source
from skoljka.apps.tags.models import Tag
from skoljka.apps.tags.utils import resolve_tags


class ProblemAdminForm(forms.Form):
    title = forms.CharField(required=False, max_length=255, label=_("Title (optional)"))
    source = forms.ModelChoiceField(
        queryset=Source.objects.none(),
        required=False,
        empty_label="— None —",
        label=_("Source"),
    )
    year = forms.IntegerField(required=False, label=_("Year"))
    problem_label = forms.CharField(required=False, max_length=32, label=_("No."))
    tags = forms.MultipleChoiceField(required=False, choices=[], label=_("Tags"))

    def __init__(self, *args, user, instance: Problem | None = None, **kwargs):
        self.user = user
        self.instance = instance
        super().__init__(*args, **kwargs)
        self.fields["source"].queryset = Source.objects.for_user(user, "edit")
        self.fields["tags"].choices = [(tag.slug, tag.slug) for tag in Tag.objects.all()]

    def save(self, request: HttpRequest) -> Problem:
        problem = self.instance or Problem()
        problem.title = self.cleaned_data["title"]
        problem.source = self.cleaned_data["source"]
        problem.year = self.cleaned_data["year"]
        problem.problem_label = self.cleaned_data["problem_label"]
        problem.save()

        tag_slugs = self.cleaned_data.get("tags") or []
        new_tag_names = request.POST.getlist("new_tags")
        problem.tags.set(resolve_tags(tag_slugs, new_tag_names))

        save_problem_content(request, problem)
        return problem

    @classmethod
    def initial_for(cls, problem: Problem | None) -> dict:
        if problem is None:
            return {}
        return {
            "title": problem.title,
            "source": problem.source_id,
            "year": problem.year,
            "problem_label": problem.problem_label,
            "tags": list(problem.tags.values_list("slug", flat=True)),
        }


def save_problem_content(request: HttpRequest, problem: Problem) -> None:
    original_language_choice = request.POST.get("original_language", "").strip()
    content_obj = problem.content.first()
    existing_langs = request.POST.getlist("existing_lang")
    texts: dict[str, str] = dict(content_obj.source_md) if content_obj else {}

    for lang in existing_langs:
        md = request.POST.get(f"content_md_{lang}", "")
        if md.strip():
            texts[lang] = md
        else:
            texts.pop(lang, None)

    default_language = (content_obj.original_language if content_obj else "") or "en"
    new_lang = request.POST.get("new_lang", "").strip() or default_language
    new_md = request.POST.get("new_md", "")
    if new_lang and new_md.strip():
        texts[new_lang] = new_md

    if texts or (content_obj and content_obj.attachments.exists()):
        if content_obj is None:
            content_obj = Content(content_object=problem)
        content_obj.source_md = texts
        if original_language_choice in texts:
            content_obj.original_language = original_language_choice
        elif content_obj.original_language not in texts:
            content_obj.original_language = next(iter(texts), new_lang or "en")
        content_obj.save()
        save_content_attachments(request, content_obj)
    elif content_obj is not None:
        content_obj.delete()


def save_content_attachments(
    request: HttpRequest,
    content_obj: Content,
    *,
    upload_field: str | None = None,
) -> None:
    upload_field = upload_field or f"content_attachments_{content_obj.id}"
    delete_field = f"delete_attachments_{content_obj.id}"

    changed = False
    for name in request.POST.getlist(delete_field):
        for attachment in content_obj.attachments.filter(name=name):
            attachment.file.delete(save=False)
            attachment.delete()
            changed = True

    for upload in request.FILES.getlist(upload_field):
        ContentAttachment.from_upload(content_obj, upload)
        changed = True

    if changed:
        content_obj.save()
