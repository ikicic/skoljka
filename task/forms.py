from django.forms.models import modelformset_factory
from django.forms.models import formset_factory
from django import forms
from task.models import Task
from mathcontent.forms import MathContentForm

class TaskAdvancedForm(forms.ModelForm):
    _tags = forms.CharField(max_length=200)
    class Meta:
        model = Task
        fields = ['name']

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['name', 'tags']
