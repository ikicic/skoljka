from django.forms.models import modelformset_factory
from django.forms.models import formset_factory
from django import forms
from models import Task
from mathcontent.forms import MathContentForm
from utils.forms import modelformlist_factory

class TaskPartForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [ 'name' ]

TaskModelFormList = modelformlist_factory(TaskPartForm, MathContentForm)
