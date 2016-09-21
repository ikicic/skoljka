from django.db import models
from django.template.loader import add_to_builtins
from django.utils.html import mark_safe

def gray_help_text(text):
    return mark_safe(
        u' <i class="help-text-gray">{}</i>'.format(text))

def icon_help_text(text):
    return mark_safe(
        u' <i class="icon-question-sign" title="{}"></i>'.format(text))

class ModelEx(models.Model):
    """
        Extension to models.Model with some utility methods.

        Please use ModelEx only if necessary, e.g. when something is repeating
        all the time, or when it would be too difficult to implement it in some
        other way.

        Excessive usage of this kind of extensions could slow down the code.
    """

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super(ModelEx, self).__init__(*args, **kwargs)
        self.remember_original()

    def save(self, *args, **kwargs):
        super(ModelEx, self).save(*args, **kwargs)
        self.remember_original()

    def remember_original(self):
        """
            Mechanism used to check whether a certain field has been changed.
            http://stackoverflow.com/a/1793323/2203044

            Override to remember here the original values of all the fields
            you want.

            This way, together with signals, you can easily implement cache
            invalidation. Of course, the method is limited to signal limits
            (e.g. filter().update() won't send signals)

            Use _original_ prefix for all those fields.

            For example:
                self._original_hidden = self.hidden
        """
        # Empty by default...
        pass

# ovo navodno nije preporuceno, ali vjerujem da ce se
# dovoljno cesto koristiti da DRY nadjaca
add_to_builtins('libs.templatetags.libs_tags')
