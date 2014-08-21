from mathcontent.forms import MathContentSmallForm

class PostsForm(MathContentSmallForm):
    def __init__(self, *args, **kwargs):
        super(PostsForm, self).__init__(*args, **kwargs)

        self.fields['text'].widget.attrs['placeholder'] = 'Komentar'
