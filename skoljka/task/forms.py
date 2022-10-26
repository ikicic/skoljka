from django import forms
from django.utils.translation import ugettext, ugettext_lazy as _

from skoljka.permissions.constants import VIEW
from skoljka.permissions.utils import filter_objects_with_permission
from skoljka.utils.models import icon_help_text

from skoljka.task.bulk_format import BulkFormatError, parse_bulk
from skoljka.task.models import Task, TaskBulkTemplate

EXPORT_FORMAT_CHOICES = (('latex', 'LaTeX'), ('pdf', 'PDF'))

class TaskBulkTemplateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.task_infos = None
        self.user = kwargs.pop('user')
        super(TaskBulkTemplateForm, self).__init__(*args, **kwargs)
        self.fields['source_code'].widget.attrs.update(
                {'rows': 20, 'cols': 100, 'class': 'uneditable-textarea'})

    def clean_name(self):
        name = self.cleaned_data['name']
        if not name:
            name = "(untitled)"
            self.cleaned_data['name'] = name
        return name

    def clean_source_code(self):
        data = self.cleaned_data['source_code']
        try:
            self.task_infos = parse_bulk(self.user, data)
        except BulkFormatError as e:
            raise forms.ValidationError(e.message)
        if not self.task_infos:
            raise forms.ValidationError(ugettext("At least one task expected."))
        return data

    class Meta:
        model = TaskBulkTemplate
        fields = ['hidden', 'name', 'source_code']


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

    def __init__(self, *args, **kwargs):
        super(TaskJSONForm, self).__init__(*args, **kwargs)

        self.fields['description'].widget.attrs.update({
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



class TaskLectureForm(TaskFileForm):
    folder_id = forms.IntegerField(required=False, help_text=icon_help_text(_(
            u"ID of the folder containing the problems and files related to "
            u"this lecture.")))

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        super(TaskFileForm, self).__init__(*args, **kwargs)

        self.fields['folder_id'].initial = \
                instance.lecture_folder_id or '' if instance else ''

    def save(self, commit=True, *args, **kwargs):
        task = super(TaskLectureForm, self).save(commit=False, *args, **kwargs)
        task.is_lecture = True
        try:
            task.lecture_folder_id = int(self.cleaned_data['folder_id'])
        except TypeError, ValueError:
            task.lecture_folder_id = None
        if commit:
            task.save()
            task.save_m2m()  # If someone later adds a many-to-many relation.
        return task

    class Meta(TaskFileForm.Meta):
        model = Task
        fields = TaskFileForm.Meta.fields + ['lecture_video_url']
