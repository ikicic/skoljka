from mathcontent.models import MathContent
from django.forms import ModelForm

class MathContentForm(ModelForm):
    class Meta:
        model = MathContent
