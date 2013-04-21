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
            queryset=q.filter(editable=True).distinct(),
            label='Roditelj')


    class Meta:
        model = Folder
        fields = ['name', 'parent', 'tags']

class FolderAdvancedCreateForm(forms.Form):
    structure = forms.CharField(widget=forms.Textarea(), label='Struktura')
    # parent = added in init...

    def __init__(self, user, *args, **kwargs):
        user = kwargs.pop('user', None)

        super(FolderAdvancedCreateForm, self).__init__(*args, **kwargs)

        # bootstrap fix
        self.fields['structure'].widget.attrs.update({
            'rows': 10, 'cols': 100, 'class': 'uneditable-textarea',
        })
        self.fields['parent'] = forms.ModelChoiceField(
            queryset=Folder.objects.for_user(user, VIEW)    \
                .filter(editable=True).distinct(),
            label='Roditelj')
