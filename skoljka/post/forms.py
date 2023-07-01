from django.utils.translation import ugettext as _

from skoljka.mathcontent.forms import MathContentSmallForm


class PostsForm(MathContentSmallForm):
    def __init__(self, *args, **kwargs):
        placeholder = kwargs.pop('placeholder', _("Comment"))
        super(PostsForm, self).__init__(*args, **kwargs)

        self.fields['text'].widget.attrs['placeholder'] = placeholder
