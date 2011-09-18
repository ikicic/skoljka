from django.forms.models import modelformset_factory
from django.forms.models import formset_factory
from django import forms
from models import Task
from mathcontent.forms import MathContentForm

class TaskPartForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [ 'name' ]

# TODO(gzuzic): refactor&move this to the utility library OR find a replacement
# TODO(gzuzic): make a prefix for different forms so no clashing occurs
class TaskModelFormList:
    FORMS = [ TaskPartForm, MathContentForm ]

    def __init__(self, values = None):
        self.forms = []
        for form in self.FORMS:
            self.forms.append(form(values))

    def __iter__(self):
        return self.forms.__iter__()

    def is_valid(self):
        self.cleaned_data = dict()
        for form in self.forms:
            if not form.is_valid():
                return False
            self.cleaned_data.update(form.cleaned_data)
        return True

    def save(self, commit=True):
        if commit:
            # commiting to the db is tricky because of order dependacies
            # it's better to leave it for the caller
            raise NotImplementedError
        return [ form.save(commit=commit) for form in self.forms ]

