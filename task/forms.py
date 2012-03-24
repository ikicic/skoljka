from django import forms
from task.models import Task
from mathcontent.forms import MathContentForm

class TaskAdvancedForm(forms.ModelForm):
    _tags = forms.CharField(max_length=200)
    _difficulty = forms.CharField(max_length=2)
    class Meta:
        model = Task
        fields = ['name', 'source', 'hidden']

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['name', 'tags', 'source', 'hidden']
