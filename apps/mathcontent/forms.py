from django.forms import ModelForm

from mathcontent.models import Attachment, MathContent


class AttachmentForm(ModelForm):
    class Meta:
        model = Attachment
        fields = ('file', )

class MathContentForm(ModelForm):
    def __init__(self, *args, **kwargs):
        blank = kwargs.pop('blank', False)
        label = kwargs.pop('label', None)
        super(MathContentForm, self).__init__(*args, **kwargs)

        if label:
            self.fields['text'].label = label
        self.fields['text'].required = not blank
        self.fields['text'].widget.attrs.update({
            'rows': 10,
            'cols': 100,
            'class': 'uneditable-textarea mathcontent-text',   # ...zbog bootstrapa
        })

    class Meta:
        model = MathContent
        fields = ('text', )

class MathContentSmallForm(MathContentForm):
    def __init__(self, *args, **kwargs):
        super(MathContentSmallForm, self).__init__(*args, **kwargs)

        self.fields['text'].label = ''
        self.fields['text'].widget.attrs.update({
            'rows': 6,
            'cols': 90,
        })