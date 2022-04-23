from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.forms.models import BaseModelFormSet, ModelForm
from django.utils.encoding import force_unicode
from django.utils.html import mark_safe
from django.utils.translation import get_language, ugettext as _, ugettext_lazy

from competition.models import Chain, CompetitionTask, Team, TeamMember
from competition.evaluator import InvalidDescriptor, InvalidSolution, \
        get_evaluator, get_solution_help_text, safe_parse_descriptor
from competition.utils import comp_url, ctask_comment_class, \
        parse_team_categories

from skoljka.libs import xss


class CompetitionSolutionForm(forms.Form):
    result = forms.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        self.descriptor = kwargs.pop('descriptor')
        self.evaluator = kwargs.pop('evaluator')
        super(CompetitionSolutionForm, self).__init__(*args, **kwargs)

    def clean_result(self):
        data = self.cleaned_data['result']
        try:
            self.evaluator.check_result(self.descriptor, data)
        except InvalidSolution as e:
            # TODO: Make a base form that automatically does this (depending on
            # a parameter).
            self.fields['result'].widget.attrs.update({
                            'class': 'ctask-submit-error'})
            raise forms.ValidationError(unicode(e))
        except InvalidDescriptor as e:
            self.fields['result'].widget.attrs.update({
                            'class': 'ctask-submit-error'})
            raise forms.ValidationError(
                    _("Descriptor error. Please notify admins!"))
        return data



class BaseCompetitionTaskFormSet(BaseModelFormSet):
    def add_fields(self, form, index):
        super(BaseCompetitionTaskFormSet, self).add_fields(form, index)
        # initial_text = form.instance.pk and form.instance.task.content.text
        # form.fields["text"] = forms.CharField(widget=forms.Textarea,
        #         initial=initial_text)



class CompetitionTaskForm(ModelForm):
    name = forms.CharField()
    text = forms.CharField(widget=forms.Textarea)
    comment = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, **kwargs):
        self.competition = kwargs.pop('competition')
        self.evaluator = get_evaluator(self.competition.evaluator_version)
        self.fixed_score = self.competition.fixed_task_score
        user = kwargs.pop('user')
        super(CompetitionTaskForm, self).__init__(*args, **kwargs)

        self.t_comment_extra_class = "ctask-comment"
        if self.instance.pk:
            self.fields['name'].initial = self.instance.task.name
            self.fields['text'].initial = self.instance.task.content.text
            self.fields['comment'].initial = self.instance.comment.text
            self.t_comment_extra_class += \
                    " " + ctask_comment_class(self.instance, user)

        descriptor = self.initial.get('descriptor')
        if descriptor:
            variables = safe_parse_descriptor(self.evaluator, descriptor)
            self.fields['descriptor'].help_text = get_solution_help_text(
                    variables, error_message=_("Invalid!"), show_types=True)
        self.fields['descriptor'].label = mark_safe(
                xss.escape(_("Solution")) + \
                ' <a href="' + comp_url(self.competition, 'rules') +
                '" target="_blank"><i class="icon-question-sign" title="' +
                xss.escape(_("Help")) + '"></i></a>')
        if not self.competition.use_custom_ctask_names():
            del self.fields['name']
        if self.fixed_score:
            del self.fields['max_score']

        self.fields['text'].widget.attrs.update(
                {'class': 'comp-mathcontent-text', 'rows': 15})
        self.fields['comment'].widget.attrs.update(
                {'class': 'comp-mathcontent-text ctask-comment', 'rows': 3})

    def clean(self):
        super(CompetitionTaskForm, self).clean()
        self.instance._text = self.cleaned_data.get('text')
        self.instance._comment = self.cleaned_data.get('comment')
        if self.fixed_score:
            self.instance.max_score = self.fixed_score
        return self.cleaned_data

    def clean_descriptor(self):
        data = self.cleaned_data['descriptor']
        try:
            variables = self.evaluator.parse_descriptor(data)
        except InvalidDescriptor as e:
            self.fields['descriptor'].help_text = ""
            raise forms.ValidationError(unicode(e))
        self.fields['descriptor'].help_text = variables[0].help_text()
        return data

    class Meta:
        model = CompetitionTask
        fields = ('descriptor', 'max_score')



class ChainForm(forms.ModelForm):
    """Form for creating or editing chains.

    For course-like competitions, the `unlock_minutes` field is replaced with
    an `unlock_days` field.
    """
    class Meta:
        model = Chain
        fields = ['name', 'category', 'unlock_minutes', 'bonus_score',
                  'position']

    def __init__(self, *args, **kwargs):
        self.competition = kwargs.pop('competition')
        super(ChainForm, self).__init__(*args, **kwargs)
        if self.competition.is_course:
            del self.fields['unlock_minutes']
            days = self.instance.unlock_minutes / (24 * 60.) \
                    if self.instance else 0
            self.fields['unlock_days'] = forms.FloatField(
                    label=_("Unlock days"), min_value=0, initial=days)

    def clean(self):
        data = self.cleaned_data
        if self.competition.is_course:
            self.cleaned_data['unlock_minutes'] = \
                    int((data['unlock_days'] or 0) * 24 * 60)
            del data['unlock_days']
        return data



def clean_unused_ctask_ids(competition, ctask_ids):
    if not ctask_ids:
        return [], []
    try:
        ctask_ids = [int(x) for x in ctask_ids.split(',')]
    except ValueError:
        raise ValidationError("Invalid input.")
    ctasks_dict = CompetitionTask.objects \
            .filter(competition=competition).in_bulk(ctask_ids)
    if len(ctask_ids) != len(ctasks_dict):
        raise ValidationError("Unknown competition task ID.")
    for ctask in ctasks_dict.itervalues():
        if ctask.chain_id is not None:
            raise ValidationError("Some tasks were already used.")
    ctasks = [ctasks_dict[id] for id in ctask_ids]
    return ctask_ids, ctasks



class ChainTasksForm(ChainForm):
    ctask_ids = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        super(ChainTasksForm, self).__init__(*args, **kwargs)

        self.fields['name'].widget.attrs.update({'class': 'span6'})
        self.fields['category'].widget.attrs.update({'class': 'span2'})
        if 'unlock_minutes' in self.fields:
            self.fields['unlock_minutes'].widget.attrs.update({'class': 'span1'})
        else:
            self.fields['unlock_days'].widget.attrs.update({'class': 'span1'})
        self.fields['bonus_score'].widget.attrs.update({'class': 'span1'})
        self.fields['position'].widget.attrs.update({'class': 'span1'})
        self.fields['ctask_ids'].widget.attrs.update(
                {'id': 'cchain-unused-ctasks-ids'})

    def clean_ctask_ids(self):
        ctask_ids, ctasks = clean_unused_ctask_ids(
                self.competition, self.cleaned_data['ctask_ids'])
        self.cleaned_data['ctasks'] = ctasks
        return ctask_ids



class TeamCategoryRadioSelectRenderer(forms.widgets.RadioFieldRenderer):
    def render(self):
        """Customize radio select render, not to use <ul>."""
        return mark_safe(u'\n'.join([force_unicode(w) for w in self]))



class TeamForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        lang = get_language()
        instance = kwargs.get('instance', None)
        initial = dict(kwargs.pop('initial', {}))
        extra_fields = []
        competition = kwargs.pop('competition')
        self.competition_id = competition.id
        self.max_team_size = kwargs.pop('max_team_size', 3)
        self.user = kwargs.pop('user')

        if instance:
            # Author cannot be removed from the team.
            team_members = list(
                    TeamMember.objects.filter(team=instance) \
                    .exclude(member_id=instance.author_id) \
                    .values_list('member_name', 'member_id'))
        else:
            team_members = []

        # Add extra fields for other members.
        for k in xrange(2, self.max_team_size + 1):
            if k - 2 < len(team_members):
                member_name = team_members[k - 2]
            else:
                member_name = ''
            field_manual = 'member{}_manual'.format(k)
            field_username = 'member{}_username'.format(k)
            initial[field_manual] = member_name
            initial[field_username] = member_name

            # Label empty because HTML generated via JavaScript anyway.
            extra_fields.append((field_manual, forms.CharField(required=False,
                label="", max_length=64)))
            extra_fields.append((field_username, forms.CharField(required=False,
                    max_length=32, widget=forms.HiddenInput())))

        # Parse team category string.
        try:
            categories = parse_team_categories(competition.team_categories, lang)
        except (ValueError, KeyError, TypeError) as e:
            categories = [(1, "team_categories invalid!!! " + e.message)]
        self.team_categories = categories
        if categories and (not instance or not instance.category):
            initial['category'] = categories[-1][0]  # For simplicity.

        super(TeamForm, self).__init__(initial=initial, *args, **kwargs)

        # Preserve order.
        for key, value in extra_fields:
            self.fields[key] = value

        self.fields['name'].widget.attrs['class'] = 'input-large'
        self.fields['name'].error_messages['required'] = \
                _("Team name cannot be empty.")

        if categories:
            self.fields['category'].widget = forms.RadioSelect(
                    choices=categories,
                    renderer=TeamCategoryRadioSelectRenderer)
        else:
            del self.fields['category']

    def _clean_member(self, index):
        manual = self.cleaned_data.get('member{}_manual'.format(index))
        username = self.cleaned_data.get('member{}_username'.format(index))

        if username and username.strip():
            username = username.strip()
            try:
                user = User.objects.get(username__iexact=username)
            except User.DoesNotExist:
                raise ValidationError(_("Unknown username \"%s\".") % username)
            if user.id == self.user.id:
                raise ValidationError(
                        _("You are automatically added to the team."))
            if TeamMember.objects.filter(
                        team__competition_id=self.competition_id,
                        member_id=user.id,
                        invitation_status=TeamMember.INVITATION_ACCEPTED) \
                    .exclude(team_id=self.instance.id) \
                    .exists():
                msg = _("User \"%s\" is already a member of a team.") % username
                raise ValidationError(msg)
            return (user.username, user)
        if manual and manual.strip():
            return (manual.strip(), None)
        return None

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if Team.objects \
                .filter(competition_id=self.competition_id, name__iexact=name) \
                .exclude(id=self.instance.id).exists():
            raise ValidationError(_("Team name already used!"))
        return name

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

        if self.team_categories:
            try:
                category = self.cleaned_data['category']
            except KeyError:
                self.cleaned_data['category'] = self.team_categories[-1][0]
            else:
                if not any(category == k for k, v in self.team_categories):
                    raise ValidationError(
                            _("Unknown team category '%s'!") % category)

        return self.cleaned_data

    class Meta:
        model = Team
        fields = ['name', 'category']



class TaskListAdminPanelForm(forms.Form):
    filter_by_team_type = forms.ChoiceField([
        (Team.TYPE_NORMAL, ugettext_lazy("Competitors")),
        (Team.TYPE_UNOFFICIAL, ugettext_lazy("Unofficial")),
        (Team.TYPE_ADMIN_PRIVATE, ugettext_lazy("Administrators")),
    ])
    filter_by_status = forms.ChoiceField([
        ('S', "Solved"), ('F', "Failed"), ('T', "Tried")])
