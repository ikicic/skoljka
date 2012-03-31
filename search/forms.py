from django import forms

from rating.widgets import RatingWidget
from rating.fields import RatingField
from rating.constants import QUALITY_RATING_ATTRS, DIFFICULTY_RATING_ATTRS
from usergroup.fields import GroupEntryField


class SearchForm(forms.Form):
    q = forms.CharField(required=False, max_length=100, label='Tags')
    show_hidden = forms.BooleanField(required=False, initial=False)

    # TODO: DRY!
    quality_min = forms.FloatField(required=False, widget=RatingWidget(attrs=QUALITY_RATING_ATTRS))
    quality_max = forms.FloatField(required=False, widget=RatingWidget(attrs=QUALITY_RATING_ATTRS))
    difficulty_min = forms.FloatField(required=False, widget=RatingWidget(attrs=DIFFICULTY_RATING_ATTRS))
    difficulty_max = forms.FloatField(required=False, widget=RatingWidget(attrs=DIFFICULTY_RATING_ATTRS))

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        
        self.fields['q'].widget.attrs.update({'class': 'ac_tags'})

class AdvancedSearchForm(forms.Form):
    groups = GroupEntryField()
