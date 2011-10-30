from django.forms.models import modelformset_factory
from django.forms.models import formset_factory
from django import forms
from task.models import Task
from mathcontent.forms import MathContentForm
from utils.forms import modelformlist_factory

class TaskPartForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [ 'name', 'tags' ]

TaskModelFormList = modelformlist_factory(TaskPartForm, MathContentForm)
