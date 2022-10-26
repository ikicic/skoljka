from django.db import models
from django.utils.translation import ugettext_lazy as _
import taggit

from skoljka.rating.fields import RatingField, SUM

CACHE_TAGS_AUTOCOMPLETE_JS_SRC = 'tags_ac_js_src'

VOTE_WRONG = -1

class Tag(taggit.models.TagBase):
    weight = models.FloatField(default=1.0)

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")

    def __unicode__(self):
        return '%s (%.1f)' % (self.name, self.weight)

class TaggedItemBase(taggit.models.ItemBase):
    tag = models.ForeignKey(Tag, related_name="%(app_label)s_%(class)s_items")

    class Meta:
        abstract = True

    # missing tags_for()

class TaggedItem(taggit.models.GenericTaggedItemBase, TaggedItemBase):
    votes = RatingField(type=SUM)

    class Meta:
        verbose_name = _("Tagged Item")
        verbose_name_plural = _("Tagged Items")
