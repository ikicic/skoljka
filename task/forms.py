from django import forms
from task.models import Task
from mathcontent.forms import MathContentForm

from taggit.utils import parse_tags

EXPORT_FORMAT_CHOICES = (('latex', 'LaTeX'), ('pdf', 'PDF'))

class TaskExportForm(forms.Form):
    format = forms.ChoiceField(choices=EXPORT_FORMAT_CHOICES)
    ids = forms.CharField(widget=forms.HiddenInput())
    has_title = forms.BooleanField(label='Naslov', required=False)
    has_url = forms.BooleanField(label='URL', required=False)
    has_source = forms.BooleanField(label='Izvor', required=False)
    has_index = forms.BooleanField(label='Broj', required=False)
    has_id = forms.BooleanField(label='ID', required=False)

    # label will be manually set later
    create_archive = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super(TaskExportForm, self).__init__(*args, **kwargs)
        self.fields['format'].widget.attrs.update({'class': 'input-small'})


class TaskAdvancedForm(forms.ModelForm):
    _tags = forms.CharField(max_length=200)
    _difficulty = forms.CharField(max_length=50)
    class Meta:
        model = Task
        fields = ['name', 'source', 'hidden']

class TaskForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)

        super(TaskForm, self).__init__(*args, **kwargs)

        self.fields['tags'].widget.attrs.update({'class': 'ac-tags span6'})
        for x in ['name', 'source']:
            self.fields[x].widget.attrs.update({'class': 'span6'})

    def clean_tags(self):
        tags = self.cleaned_data['tags']
        # temporary solution
        if self.user and not self.user.is_staff:
            if any(('news' == x.strip().lower() for x in tags)):
                raise forms.ValidationError("Tag 'news' nije dozvoljen!")
        return tags

    class Meta:
        model = Task
        fields = ['name', 'tags', 'source', 'hidden']
