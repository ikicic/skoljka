from django import forms
from django.utils.translation import gettext_lazy as _

from skoljka.apps.tags.models import Tag


def _translation_dict(en: str, hr: str) -> dict[str, str]:
    result: dict[str, str] = {}
    if en:
        result["en"] = en
    if hr:
        result["hr"] = hr
    return result


class TagAdminForm(forms.Form):
    slug = forms.SlugField(
        label=_("Slug"),
        error_messages={"required": _("Slug is required.")},
    )
    kind = forms.ChoiceField(choices=Tag.Kind.choices, label=_("Kind"))
    parent = forms.ModelChoiceField(
        queryset=Tag.objects.none(),
        required=False,
        empty_label="—",
        label=_("Parent"),
    )
    hidden = forms.BooleanField(required=False, label=_("Hidden"))
    name_en = forms.CharField(
        label=_("Name (EN)"),
        error_messages={"required": _("Name (EN) is required.")},
    )
    name_hr = forms.CharField(required=False, label=_("Name (HR)"))
    short_name_en = forms.CharField(required=False, label=_("Short name (EN)"))
    short_name_hr = forms.CharField(required=False, label=_("Short name (HR)"))
    description_en = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        label=_("Description (EN)"),
    )
    description_hr = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        label=_("Description (HR)"),
    )

    def __init__(self, *args, instance: Tag | None = None, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)
        parent_qs = Tag.objects.all()
        if instance is not None:
            parent_qs = parent_qs.exclude(pk=instance.pk)
        self.fields["parent"].queryset = parent_qs

    def clean_slug(self):
        slug = self.cleaned_data["slug"]
        qs = Tag.objects.filter(slug=slug)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_("A tag with this slug already exists."))
        return slug

    def clean_parent(self):
        parent = self.cleaned_data.get("parent")
        if parent is not None and self.instance is not None and parent.pk == self.instance.pk:
            raise forms.ValidationError(_("A tag cannot be its own parent."))
        return parent

    def save(self) -> Tag:
        tag = self.instance or Tag()
        tag.slug = self.cleaned_data["slug"]
        tag.kind = self.cleaned_data["kind"]
        tag.parent = self.cleaned_data["parent"]
        tag.hidden = self.cleaned_data["hidden"]
        tag.translations = _translation_dict(
            self.cleaned_data["name_en"],
            self.cleaned_data["name_hr"],
        )
        tag.short_translations = _translation_dict(
            self.cleaned_data["short_name_en"],
            self.cleaned_data["short_name_hr"],
        )
        tag.descriptions = _translation_dict(
            self.cleaned_data["description_en"],
            self.cleaned_data["description_hr"],
        )
        tag.save()
        return tag

    @classmethod
    def initial_for(cls, tag: Tag | None) -> dict:
        if tag is None:
            return {"kind": Tag.Kind.TOPIC}
        return {
            "slug": tag.slug,
            "kind": tag.kind,
            "parent": tag.parent_id,
            "hidden": tag.hidden,
            "name_en": tag.translations.get("en", ""),
            "name_hr": tag.translations.get("hr", ""),
            "short_name_en": tag.short_translations.get("en", ""),
            "short_name_hr": tag.short_translations.get("hr", ""),
            "description_en": tag.descriptions.get("en", ""),
            "description_hr": tag.descriptions.get("hr", ""),
        }
