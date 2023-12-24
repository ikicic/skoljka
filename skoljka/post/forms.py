from django.utils.translation import ugettext as _

from skoljka.mathcontent.forms import MathContentForm, MathContentSmallForm


class PostsLargeForm(MathContentForm):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('prefix', 'posts')
        super(PostsLargeForm, self).__init__(*args, **kwargs)


class PostsForm(MathContentSmallForm):
    def __init__(self, *args, **kwargs):
        placeholder = kwargs.pop('placeholder', _("Comment"))
        kwargs.setdefault('prefix', 'posts')
        super(PostsForm, self).__init__(*args, **kwargs)

        self.fields['text'].widget.attrs['placeholder'] = placeholder
