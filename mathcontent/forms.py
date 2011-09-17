from models import MathContentText
from django.forms import ModelForm

# Don't use this unless you know what you're doing
class MathContentTextForm(ModelForm):
    class Meta:
        model = MathContentText

# TODO(gzuzic): This will be substantially changed
#               when other content types are added
# Use this one instead
MathContentForm = MathContentTextForm
