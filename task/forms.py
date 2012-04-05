from django import forms
from task.models import Task
from mathcontent.forms import MathContentForm

class TaskAdvancedForm(forms.ModelForm):
    _tags = forms.CharField(max_length=200)
    _difficulty = forms.CharField(max_length=50)
    class Meta:
        model = Task
        fields = ['name', 'source', 'hidden']

class TaskForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        
        self.fields['tags'].widget.attrs.update({'class': 'ac_tags span4'})
        for x in ['name', 'source']:
            self.fields[x].widget.attrs.update({'class': 'span4'})

    class Meta:
        model = Task
        fields = ['name', 'tags', 'source', 'hidden']
