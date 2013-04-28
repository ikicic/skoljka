from tags.models import TaggedItem
from django.utils.translation import ugettext_lazy as _

from taggit import managers

from skoljka.utils.models import icon_help_text

# TODO: signals!
class TaggableManager(managers.TaggableManager):
    def __init__(self, verbose_name=_("Tags"),
            help_text=icon_help_text('Popis oznaka, odvojene zarezom. Npr. IMO, komb, igra'),
            through=None, blank=False):
        through = through or TaggedItem
        super(TaggableManager, self).__init__(verbose_name, help_text, through, blank)
