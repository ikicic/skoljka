from django import forms
from django.utils.translation import ugettext
from django.utils.translation import ugettext_lazy as _

from skoljka.task.bulk_format import BulkFormatError, parse_bulk
from skoljka.task.models import Task, TaskBulkTemplate
from skoljka.utils.models import icon_help_text

EXPORT_FORMAT_CHOICES = (('latex', 'LaTeX'), ('pdf', 'PDF'))


class TaskBulkTemplateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.task_infos = None
        self.user = kwargs.pop('user')
        super(TaskBulkTemplateForm, self).__init__(*args, **kwargs)
        self.fields['source_code'].widget.attrs.update(
            {'rows': 20, 'cols': 100, 'class': 'uneditable-textarea'}
        )

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
    has_title = forms.BooleanField(label=_("Title"), required=False)
    has_url = forms.BooleanField(label=_("URL"), required=False)
    has_source = forms.BooleanField(label=_("Source"), required=False)
    has_index = forms.BooleanField(label=_("Index"), required=False)
    has_id = forms.BooleanField(label=_("ID"), required=False)

    # label will be manually set later
    create_archive = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super(TaskExportForm, self).__init__(*args, **kwargs)
        self.fields['format'].widget.attrs.update({'class': 'input-small'})


class TaskJSONForm(forms.Form):
    description = forms.CharField(widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super(TaskJSONForm, self).__init__(*args, **kwargs)

        self.fields['description'].widget.attrs.update(
            {
                'rows': 10,
                'cols': 100,
                'class': 'uneditable-textarea',  # bootstrap...
            }
        )


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
                raise forms.ValidationError(_("The tag 'news' is not allowed."))
        return tags

    class Meta:
        # Currently, you will have to manually add new fields to the template.
        model = Task
        fields = [
            'name',
            'tags',
            'source',
            'hidden',
            'solvable',
        ]


class TaskFileForm(TaskForm):
    def __init__(self, *args, **kwargs):
        super(TaskFileForm, self).__init__(*args, **kwargs)

        self.fields['solvable'].initial = False


class TaskLectureForm(TaskFileForm):
    folder_id = forms.IntegerField(
        required=False,
        help_text=icon_help_text(
            _(
                u"ID of the folder containing the problems and files related to "
                u"this lecture."
            )
        ),
    )

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        super(TaskFileForm, self).__init__(*args, **kwargs)

        self.fields['folder_id'].initial = (
            instance.lecture_folder_id or '' if instance else ''
        )

    def save(self, commit=True, *args, **kwargs):
        task = super(TaskLectureForm, self).save(commit=False, *args, **kwargs)
        task.is_lecture = True
        try:
            task.lecture_folder_id = int(self.cleaned_data['folder_id'])
        except (TypeError, ValueError):
            task.lecture_folder_id = None
        if commit:
            task.save()
            task.save_m2m()  # If someone later adds a many-to-many relation.
        return task

    class Meta(TaskFileForm.Meta):
        model = Task
        fields = TaskFileForm.Meta.fields + ['lecture_video_url']
