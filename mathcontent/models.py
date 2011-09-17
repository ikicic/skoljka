from django.db import models
from django.template.loader import render_to_string

class MathContent(models.Model):
    pass

class TextContent(MathContent):
    text = models.TextField();

    def __unicode__(self):
        if len(self.text) > 72:
            return self.text[:72] + "..."
        else:
            return self.text

    def render(self):
        return render_to_string('textcontent.html', {'text': self.text})
