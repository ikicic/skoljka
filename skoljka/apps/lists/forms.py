from django import forms
from django.utils.translation import gettext_lazy as _

from skoljka.apps.lists.models import ProblemList


class ProblemListForm(forms.Form):
    title = forms.CharField(
        max_length=255,
        label=_("Title"),
        error_messages={"required": _("Title is required.")},
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        label=_("Description"),
    )
    public = forms.BooleanField(required=False, label=_("Public"))

    def save(self, user, instance: ProblemList | None = None) -> ProblemList:
        is_public = self.cleaned_data["public"]
        if instance is None:
            return ProblemList.objects.create(
                title=self.cleaned_data["title"],
                description=self.cleaned_data["description"],
                is_public=is_public,
                created_by=user,
            )
        instance.title = self.cleaned_data["title"]
        instance.description = self.cleaned_data["description"]
        instance.is_public = is_public
        instance.save()
        return instance
