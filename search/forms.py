from django import forms

from rating.widgets import RatingWidget
from rating.fields import RatingField
from rating.constants import QUALITY_RATING_ATTRS, DIFFICULTY_RATING_ATTRS


class SearchForm(forms.Form):
    q = forms.CharField(required=False, max_length=100, label='Tags')
    show_hidden = forms.BooleanField(required=False, initial=False)

    # TODO: DRY!
    quality_min = forms.FloatField(required=False, widget=RatingWidget(attrs=QUALITY_RATING_ATTRS))
    quality_max = forms.FloatField(required=False, widget=RatingWidget(attrs=QUALITY_RATING_ATTRS))
    difficulty_min = forms.FloatField(required=False, widget=RatingWidget(attrs=DIFFICULTY_RATING_ATTRS))
    difficulty_max = forms.FloatField(required=False, widget=RatingWidget(attrs=DIFFICULTY_RATING_ATTRS))
    