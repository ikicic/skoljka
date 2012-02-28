from tags.models import TaggedItem
from django.utils.translation import ugettext_lazy as _

from taggit import managers

class TaggableManager(managers.TaggableManager):
    def __init__(self, verbose_name=_("Tags"),
        help_text=_("A comma-separated list of tags."), through=None, blank=False):
        through = through or TaggedItem
        super(TaggableManager, self).__init__(verbose_name, help_text, through, blank)
