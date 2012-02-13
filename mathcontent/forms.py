from mathcontent.models import MathContent
from django.forms import ModelForm

class MathContentForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(MathContentForm, self).__init__(*args, **kwargs)
        
        self.fields['text'].widget.attrs['rows'] = 10
        self.fields['text'].widget.attrs['cols'] = 120

    class Meta:
        model = MathContent
