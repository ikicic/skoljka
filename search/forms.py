from django import forms


class SearchForm(forms.Form):
    q = forms.CharField(required=False, max_length=100, label='Tags')
    show_hidden = forms.BooleanField(required=False, initial=False)