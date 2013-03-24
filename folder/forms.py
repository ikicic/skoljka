from django import forms

from permissions.constants import VIEW

from folder.models import Folder

class FolderForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)

        if self.user.has_perm('can_publish_folders') or True:
            self.Meta.fields.append('hidden')

        super(FolderForm, self).__init__(*args, **kwargs)

        # User can put his folder anywhere he wants (into any visible folder),
        # but that doesn't mean he can make it public!

        q = Folder.objects.for_user(self.user, VIEW)
        if self.instance:
            q = q.exclude(id=self.instance.id)

        self.fields['parent'] = forms.ModelChoiceField(
            queryset=q.distinct(),
            label='Roditelj')


    class Meta:
        model = Folder
        fields = ['name', 'parent', 'tag_filter', 'structure']
