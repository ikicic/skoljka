from django import forms

from permissions.constants import VIEW

from folder.models import Folder
from folder.utils import get_visible_folder_tree

class FolderForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)

        if self.user.has_perm('can_publish_folders') or True:
            self.Meta.fields.append('hidden')

        super(FolderForm, self).__init__(*args, **kwargs)

        # User can put his folder anywhere he wants (into any visible folder),
        # but that doesn't mean he can make it public!

        # Check all permissions. Remove inaccessible folders
        data = get_visible_folder_tree(Folder.objects.filter(editable=True),
            self.user)


        # WARNING: Do not forget to remove self.instance from the list!
        exclude_id = self.instance.id if self.instance else None

        # Keep only editable folders (maybe some folders are in the tree, but
        # not editable). Convert to choice pairs.
        self._parent_choices = filter(
            lambda x: x.editable and x.id != exclude_id, data['sorted_folders'])
        choices = [(x.id, '-- ' * (x._depth - 1) + x.name)
            for x in self._parent_choices]

        self.fields['parent'] = forms.ChoiceField(
            choices=choices, label='Roditelj')

    def clean_parent(self):
        data = self.cleaned_data.get('parent')
        folder = next((x for x in self._parent_choices if data == unicode(x.id)), None)

        if not folder:
            raise forms.ValidationError('Nevaljana kolekcija.')

        return folder

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
