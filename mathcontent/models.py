from django.db import models
from django.template.loader import render_to_string
from model_utils.managers import InheritanceManager

# TODO(gzuzic): measure the number of SQL queries made and whether can it be improved

class MathContent(models.Model):
    objects = InheritanceManager();

    def __unicode__(self):
        """Polymorphically call a deriving class member __unicode__()"""
        return MathContent.objects.select_subclasses().get(id=self.id).__unicode__()

    def render(self):
        """Polymorphically call a deriving class member render()"""
        return MathContent.objects.select_subclasses().get(id=self.id).render()

class MathContentText(MathContent):
    text = models.TextField();

    def __unicode__(self):
        return self.text

    def render(self):
        return render_to_string('mathcontenttext.html', {'text': self.text})
