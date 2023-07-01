from django import forms

from skoljka.rating.widgets import RatingWidget
from skoljka.task.models import DIFFICULTY_RATING_ATTRS, QUALITY_RATING_ATTRS
from skoljka.usergroup.fields import GroupEntryField


class SearchForm(forms.Form):
    q = forms.CharField(required=False, max_length=100, label='Tags')
    show_hidden = forms.BooleanField(required=False, initial=False, label='Skriveni')

    quality_min = forms.FloatField(
        required=False,
        widget=RatingWidget(attrs=QUALITY_RATING_ATTRS),
        label="Kvaliteta min.",
    )
    quality_max = forms.FloatField(
        required=False,
        widget=RatingWidget(attrs=QUALITY_RATING_ATTRS),
        label="Kvaliteta max.",
    )
    difficulty_min = forms.FloatField(
        required=False,
        widget=RatingWidget(attrs=DIFFICULTY_RATING_ATTRS),
        label=u"Težina min.",
    )
    difficulty_max = forms.FloatField(
        required=False,
        widget=RatingWidget(attrs=DIFFICULTY_RATING_ATTRS),
        label=u"Težina max.",
    )

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)

        self.fields['q'].widget.attrs.update({'class': 'ac-tags'})


class AdvancedSearchForm(forms.Form):
    groups = GroupEntryField(label='Grupe', required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')  # user must be given!
        super(AdvancedSearchForm, self).__init__(*args, **kwargs)
        self.fields['groups'].user = user
