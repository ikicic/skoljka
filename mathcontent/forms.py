from mathcontent.models import MathContent
from django.forms import ModelForm

class MathContentForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(MathContentForm, self).__init__(*args, **kwargs)
        
        self.fields['text'].widget.attrs.update({
            'rows': 10,
            'cols': 100,
            'class': 'uneditable-textarea',   # ...zbog bootstrapa
        })

    class Meta:
        model = MathContent
