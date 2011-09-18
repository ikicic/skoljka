from django import forms

class SubmitForm(forms.Form):
    content = forms.CharField(min_length=1, max_length=2000, widget=forms.Textarea)

