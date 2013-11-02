from django import forms
from task.models import Task
from mathcontent.forms import MathContentForm

from taggit.utils import parse_tags

from permissions.constants import VIEW
from permissions.utils import filter_objects_with_permission

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

class TaskJSONForm(forms.Form):
    description = forms.CharField(widget=forms.Textarea)
    common = forms.CharField(widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super(TaskJSONForm, self).__init__(*args, **kwargs)

        for x in ['description', 'common']:
            self.fields[x].widget.attrs.update({
                'rows': 10,
                'cols': 100,
                'class': 'uneditable-textarea', # bootstrap...
            })


class TaskAdvancedForm(forms.ModelForm):
    _tags = forms.CharField(max_length=200)
    _difficulty = forms.CharField(max_length=50)
    class Meta:
        model = Task
        fields = ['name', 'source', 'hidden']

def check_prerequisites(prerequisites, user, task_id):
    """
        Check if all given ids are accessible.
        Returns the list of ids and list of accessible task instances.
    """
    if not prerequisites.strip():
        return [], []

    try:
        # Remove duplicates
        ids = set([int(x) for x in prerequisites.split(',')])
    except ValueError:
        raise forms.ValidationError('Nevaljan format!')

    if task_id and task_id in ids:
        raise forms.ValidationError(u'Zadatak ne može biti sam sebi preduvjet!')

    tasks = Task.objects.filter(id__in=ids)
    accessible = filter_objects_with_permission(tasks, user, VIEW, model=Task)

    if len(ids) != len(accessible):
        diff = ids - set(x.id for x in accessible)
        raise forms.ValidationError('Nepoznati ili nedostupni zadaci: {}' \
            .format(', '.join(str(x) for x in diff)))

    for x in accessible:
        if not x.solvable:
            raise forms.ValidationError(
                u'Nije moguće slati rješenja za zadatak #{}!'.format(x.id))

    return ids, accessible

class TaskForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)

        super(TaskForm, self).__init__(*args, **kwargs)

        task_id = str(self.instance.id) if self.instance and self.instance.id else ''
        self.fields['prerequisites'].widget.attrs.update(
            {'class': 'task-prerequisites', 'data-task-id': task_id})
        self.fields['tags'].widget.attrs.update({'class': 'ac-tags span6'})
        for x in ['name', 'source']:
            self.fields[x].widget.attrs.update({'class': 'span6'})

    def clean(self):
        cleaned_data = super(TaskForm, self).clean()
        if self.cleaned_data['solution_settings'] == Task.SOLUTIONS_VISIBLE \
                and self.cleaned_data.get('prerequisites'):
            raise forms.ValidationError(u'Ukoliko su postavljeni preduvjeti, '
                u'rješenja ne mogu biti \'uvijek vidljiva\'!')
        return self.cleaned_data

    def clean_tags(self):
        tags = self.cleaned_data['tags']
        # temporary solution
        if self.user and not self.user.is_staff:
            if any(('news' == x.strip().lower() for x in tags)):
                raise forms.ValidationError("Oznaka 'news' nije dozvoljena!")
        return tags

    def clean_prerequisites(self):
        # Trim whitespace.
        prerequisites = self.cleaned_data['prerequisites'].strip()
        self.cleaned_data['prerequisites'] = prerequisites

        # This will raise an exception if something is wrong.
        check_prerequisites(prerequisites, self.user,
            self.instance and self.instance.id)

        return prerequisites

    class Meta:
        # Currently, you will have to manually add new fields to the template.
        model = Task
        fields = ['name', 'tags', 'source', 'hidden', 'solvable',
            'solution_settings', 'prerequisites']

class TaskFileForm(TaskForm):
    def __init__(self, *args, **kwargs):
        super(TaskFileForm, self).__init__(*args, **kwargs)

        self.fields['solvable'].initial = False
