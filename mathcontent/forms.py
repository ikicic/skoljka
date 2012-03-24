from django.forms import ModelForm

from mathcontent.models import Attachment, MathContent


class AttachmentForm(ModelForm):
    class Meta:
        model = Attachment
        fields = ('file', )

class MathContentForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(MathContentForm, self).__init__(*args, **kwargs)
        
        self.fields['text'].widget.attrs.update({
            'rows': 10,
            'cols': 100,
            'class': 'uneditable-textarea mathcontent_text',   # ...zbog bootstrapa
        })

    class Meta:
        model = MathContent
        fields = ('text', )
