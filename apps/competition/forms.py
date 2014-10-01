from django import forms
from django.contrib.auth.models import User
from django.forms.models import BaseModelFormSet, ModelForm

from competition.models import Chain, CompetitionTask, Team, TeamMember


class BaseCompetitionTaskFormSet(BaseModelFormSet):
    def add_fields(self, form, index):
        super(BaseCompetitionTaskFormSet, self).add_fields(form, index)
        # initial_text = form.instance.pk and form.instance.task.content.text
        # form.fields["text"] = forms.CharField(widget=forms.Textarea,
        #         initial=initial_text)

class CompetitionTaskForm(ModelForm):
    text = forms.CharField(widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super(CompetitionTaskForm, self).__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['text'].initial = self.instance.task.content.text

        self.fields['text'].widget.attrs.update({
            'rows': 5,
            'class': 'comp-mathcontent-text',
        })

    def clean(self):
        super(CompetitionTaskForm, self).clean()
        self.instance._text = self.cleaned_data.get('text')
        return self.cleaned_data

    class Meta:
        model = CompetitionTask
        fields = ('correct_result', 'score')

class ChainForm(forms.ModelForm):
    class Meta:
        model = Chain
        fields = ['name', 'category', 'unlock_minutes']

class TeamForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        initial = kwargs.pop('initial', {})
        extra_fields = []
        self.max_team_size = kwargs.pop('max_team_size', 3)

        if instance:
            # Author cannot be removed from the team.
            team_members = list(TeamMember.objects.filter(team=instance) \
                    .exclude(member_id=instance.author_id) \
                    .values_list('member_name', 'member_id'))
        else:
            team_members = []

        # Add extra fields for other members
        for k in xrange(2, self.max_team_size + 1):
            label = u'{}. \u010dlan'.format(k)
            if k - 2 < len(team_members):
                username, user_id = team_members[k - 2]
            else:
                username = user_id = ''
            key = 'member{}_manual'.format(k)
            key_id = 'member{}_user_id'.format(k)
            initial[key] = username
            initial[key_id] = user_id

            extra_fields.append((key, forms.CharField(required=False,
                label=label, max_length=64)))
            extra_fields.append((key_id, forms.CharField(required=False,
                    max_length=32, widget=forms.HiddenInput())))

        super(TeamForm, self).__init__(initial=initial, *args, **kwargs)

        # Preserve order
        for key, value in extra_fields:
            self.fields[key] = value


    def _clean_member(self, index):
        manual = self.cleaned_data.get('member{}_manual'.format(index))
        user_id = self.cleaned_data.get('member{}_user_id'.format(index))

        if user_id:
            user = User.objects.get(id=user_id)
            return (user.username, user)
        if manual and manual.strip():
            return (manual.strip(), None)
        return None

    def clean(self):
        members = []
        ids = set()
        for k in xrange(2, self.max_team_size + 1):
            member = self._clean_member(k)
            if not member:
                continue
            if isinstance(member[1], User):
                if member[1].id not in ids:
                    ids.add(member[1].id)
                    members.append(member)
            else:
                members.append(member)

        self._members = members

        return self.cleaned_data

    class Meta:
        model = Team
        fields = ['name']
