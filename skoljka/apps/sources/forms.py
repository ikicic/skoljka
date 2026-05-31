from django import forms
from django.utils.translation import gettext_lazy as _

from skoljka.apps.sources.models import Source
from skoljka.apps.tags.utils import resolve_tags


class SourceDetailsForm(forms.Form):
    slug = forms.SlugField(
        label=_("Slug"),
        error_messages={"required": _("Slug is required.")},
    )
    name_en = forms.CharField(
        label=_("Name (EN)"),
        error_messages={"required": _("Name (EN) is required.")},
    )
    name_hr = forms.CharField(required=False, label=_("Name (HR)"))
    description_en = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label=_("Description (EN)"),
    )
    parent = forms.ModelChoiceField(
        queryset=Source.objects.none(),
        required=False,
        empty_label="— None —",
        label=_("Parent"),
    )
    order = forms.IntegerField(initial=0, label=_("Order"))
    tags = forms.MultipleChoiceField(required=False, choices=[], label=_("Tags"))

    def __init__(self, *args, user, instance: Source | None = None, **kwargs):
        self.user = user
        self.instance = instance
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = Source.objects.for_user(user, "edit")
        if instance is not None:
            self.fields["parent"].queryset = self.fields["parent"].queryset.exclude(pk=instance.pk)

    def clean_slug(self):
        slug = self.cleaned_data["slug"]
        qs = Source.objects.filter(slug=slug)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_("A source with this slug already exists."))
        return slug

    def clean_parent(self):
        parent = self.cleaned_data.get("parent")
        if parent is None:
            return None
        try:
            return Source.objects.for_user(self.user, "edit").get(pk=parent.pk)
        except Source.DoesNotExist:
            raise forms.ValidationError(_("Parent source not found."))

    def save(self) -> Source:
        source = self.instance or Source()
        source.slug = self.cleaned_data["slug"]
        source.order = self.cleaned_data["order"]
        source.parent = self.cleaned_data["parent"]

        translations = source.translations.copy() if source.translations else {}
        en = translations.get("en", {})
        en["name"] = self.cleaned_data["name_en"]
        description_en = self.cleaned_data["description_en"]
        if description_en:
            en["description"] = description_en
        else:
            en.pop("description", None)
        translations["en"] = en
        name_hr = self.cleaned_data["name_hr"]
        if name_hr:
            hr = translations.get("hr", {})
            hr["name"] = name_hr
            translations["hr"] = hr
        else:
            translations.pop("hr", None)
        source.translations = translations
        source.save()
        source.tags.set(resolve_tags(self.cleaned_data.get("tags") or []))
        return source

    @classmethod
    def initial_for(cls, source: Source | None) -> dict:
        if source is None:
            return {"order": 0}
        en = source.translations.get("en", {}) if source.translations else {}
        hr = source.translations.get("hr", {}) if source.translations else {}
        return {
            "slug": source.slug,
            "name_en": en.get("name", ""),
            "name_hr": hr.get("name", ""),
            "description_en": en.get("description", ""),
            "parent": source.parent_id,
            "order": source.order,
            "tags": list(source.tags.values_list("slug", flat=True)),
        }


class SourceChildrenForm(forms.Form):
    """Validate parallel child_* POST lists for the source children editor."""

    def __init__(self, data, *, source: Source, user, **kwargs):
        self.source = source
        self.user = user
        self.rows = self._parse_rows(data)
        super().__init__(data, **kwargs)

    @staticmethod
    def _list_get(values: list[str], index: int) -> str:
        return values[index] if index < len(values) else ""

    def _parse_rows(self, data) -> list[dict]:
        child_ids = data.getlist("child_id")
        slugs = data.getlist("child_slug")
        names_en = data.getlist("child_name_en")
        names_hr = data.getlist("child_name_hr")
        orders = data.getlist("child_order")
        max_len = max(len(child_ids), len(slugs), len(names_en), len(names_hr), len(orders))
        rows: list[dict] = []
        for i in range(max_len):
            child_id = self._list_get(child_ids, i)
            slug = self._list_get(slugs, i).strip()
            name_en = self._list_get(names_en, i).strip()
            name_hr = self._list_get(names_hr, i).strip()
            order_raw = self._list_get(orders, i).strip() or "0"
            if not child_id and not slug and not name_en and not name_hr:
                continue
            rows.append(
                {
                    "child_id": child_id,
                    "slug": slug,
                    "name_en": name_en,
                    "name_hr": name_hr,
                    "order_raw": order_raw,
                    "row_number": i + 1,
                }
            )
        return rows

    def clean(self):
        cleaned = super().clean()
        errors: list[str] = []
        for row in self.rows:
            n = row["row_number"]
            if not row["slug"]:
                errors.append(_("Child row %(number)s: slug is required.") % {"number": n})
            if not row["name_en"]:
                errors.append(_("Child row %(number)s: Name (EN) is required.") % {"number": n})
            try:
                row["order"] = int(row["order_raw"])
            except (TypeError, ValueError):
                errors.append(_("Child row %(number)s: order must be an integer.") % {"number": n})
                row["order"] = 0

        for row in self.rows:
            if "order" not in row:
                row["order"] = 0
            if not row.get("slug"):
                continue
            qs = Source.objects.filter(slug=row["slug"])
            if row["child_id"]:
                qs = qs.exclude(pk=row["child_id"])
            if qs.exists():
                errors.append(
                    _("Child row %(number)s: a source with this slug already exists.")
                    % {"number": row["row_number"]}
                )

        if errors:
            raise forms.ValidationError(errors)
        return cleaned

    def save(self) -> None:
        for row in self.rows:
            child_id = row["child_id"]
            if child_id:
                try:
                    child = Source.objects.for_user(self.user, "edit").get(
                        pk=child_id, parent=self.source
                    )
                except (Source.DoesNotExist, ValueError):
                    continue
            else:
                child = Source(parent=self.source)
            child.slug = row["slug"]
            child.order = row["order"]
            translations = child.translations.copy() if child.translations else {}
            translations["en"] = {**translations.get("en", {}), "name": row["name_en"]}
            if row["name_hr"]:
                translations["hr"] = {**translations.get("hr", {}), "name": row["name_hr"]}
            else:
                translations.pop("hr", None)
            child.translations = translations
            child.save()
