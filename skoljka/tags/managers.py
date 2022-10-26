from django.utils.translation import ugettext_lazy as _
from taggit.forms import TagField as taggit_TagField
from taggit.managers import TaggableManager as taggit_TaggableManager

from skoljka.utils.models import icon_help_text

from skoljka.tags.models import TaggedItem
from skoljka.tags.utils import replace_with_original_tags

class CaseInsensitiveTagField(taggit_TagField):
    def clean(self, value):
        """
            Replace all tags with their existing version, i.e. fix cases.
            Unknown tags won't be changed.
        """
        value = super(CaseInsensitiveTagField, self).clean(value)

        return replace_with_original_tags(value)


# TODO: signals!
class TaggableManager(taggit_TaggableManager):
    def __init__(self, verbose_name=_("Tags"),
            help_text=icon_help_text(
                "Popis oznaka, odvojene zarezom. Npr. IMO, komb, igra"),
            through=None, blank=False):
        through = through or TaggedItem
        super(TaggableManager, self).__init__(verbose_name, help_text, through, blank)

    def formfield(self, form_class=CaseInsensitiveTagField, **kwargs):
        """
            Replace original TagField with a custom one.
        """
        return super(TaggableManager, self).formfield(
            form_class=form_class, **kwargs)
