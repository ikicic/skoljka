from django import forms

from permissions.constants import VIEW

from folder.models import Folder
from folder.utils import get_visible_folder_tree

class FolderForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.initial_parent_id = kwargs.pop('initial_parent_id', None)

        super(FolderForm, self).__init__(*args, **kwargs)

        if not self.user.has_perm('can_publish_folders'):
            del self.fields['hidden']
        if not self.user.has_perm('can_set_short_name'):
            del self.fields['short_name']

        # User can put his folder anywhere he wants (into any visible folder),
        # but that doesn't mean he can make it public!

        # Check all permissions. Remove inaccessible folders.
        # WARNING: Remove the subtree of the given folder!
        data = get_visible_folder_tree(Folder.objects.filter(editable=True),
            self.user, exclude_subtree=self.instance)

        # WARNING: Do not forget to remove self.instance from the list!
        exclude_id = self.instance.id if self.instance else None

        # Keep only editable folders (maybe some folders are in the tree, but
        # not editable). Convert to choice pairs.
        root = Folder.objects.get(parent_id__isnull=True)
        root._depth = 0
        self._parent_choices = [root]
        self._parent_choices.extend(filter(
            lambda x: x.editable and x.id != exclude_id, data['sorted_folders']
        ))
        choices = [(x.id, '-- ' * (x._depth - 1) + x.name)
            for x in self._parent_choices]

        # Make sure initial parent exist and it's accessible
        self.initial_parent = next(
            (x for x in self._parent_choices if self.initial_parent_id == x.id),
            None,
        )

        if not self.initial_parent:
            self.initial_parent_id = None

        self.fields['parent'] = forms.ChoiceField(
            choices=choices, label='Roditelj', initial=self.initial_parent_id)

    def clean_parent(self):
        data = self.cleaned_data.get('parent')
        folder = next((x for x in self._parent_choices if data == unicode(x.id)), None)

        if not folder:
            raise forms.ValidationError('Nevaljana kolekcija.')

        return folder

    class Meta:
        model = Folder
        fields = ['name', 'short_name', 'parent', 'tags', 'hidden']

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
