from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.forms.models import BaseModelFormSet, ModelForm
from django.utils.encoding import force_unicode
from django.utils.html import mark_safe
from django.utils.translation import get_language
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy

from skoljka.competition.evaluator import (
    get_evaluator,
    get_solution_help_text,
    safe_parse_descriptor,
)
from skoljka.competition.evaluator_base import InvalidDescriptor, InvalidSolution
from skoljka.competition.models import Chain, CompetitionTask, Team, TeamMember
from skoljka.competition.utils import comp_url, ctask_comment_class
from skoljka.utils import xss
from skoljka.utils.python23 import unicode


class SubmissionForm(forms.Form):
    result = forms.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        self.descriptor = kwargs.pop('descriptor')
        self.evaluator = kwargs.pop('evaluator')
        super(SubmissionForm, self).__init__(*args, **kwargs)

    def clean_result(self):
        data = self.cleaned_data['result']
        try:
            self.evaluator.check_result(self.descriptor, data)
        except InvalidSolution as e:
            # TODO: Make a base form that automatically does this (depending on
            # a parameter).
            self.fields['result'].widget.attrs.update({'class': 'ctask-submit-error'})
            raise forms.ValidationError(unicode(e))
        except InvalidDescriptor:
            self.fields['result'].widget.attrs.update({'class': 'ctask-submit-error'})
            raise forms.ValidationError(_("Descriptor error. Please notify admins!"))
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
        competition = kwargs.pop('competition')
        self.competition = competition
        self.evaluator = get_evaluator(competition.evaluator_version)
        self.fixed_score = competition.fixed_task_score
        user = kwargs.pop('user')
        super(CompetitionTaskForm, self).__init__(*args, **kwargs)

        self.t_comment_extra_class = "ctask-comment"
        self.fields['max_submissions'].initial = competition.default_max_submissions
        if self.instance.pk:
            self.fields['name'].initial = self.instance.task.name
            self.fields['text'].initial = self.instance.task.content.text
            self.fields['comment'].initial = self.instance.comment.text
            self.t_comment_extra_class += " " + ctask_comment_class(self.instance, user)

        descriptor = self.initial.get('descriptor')
        if descriptor:
            variables = safe_parse_descriptor(self.evaluator, descriptor)
            self.fields['descriptor'].help_text = get_solution_help_text(
                variables, error_message=_("Invalid!"), show_types=True
            )
        self.fields['descriptor'].label = mark_safe(
            xss.escape(_("Solution"))
            + ' <a href="'
            + comp_url(competition, 'rules')
            + '" target="_blank"><i class="icon-question-sign" title="'
            + xss.escape(_("Help"))
            + '"></i></a>'
        )
        if not competition.use_custom_ctask_names():
            del self.fields['name']
        if self.fixed_score:
            del self.fields['max_score']

        self.fields['text'].widget.attrs.update(
            {'class': 'comp-mathcontent-text', 'rows': 15}
        )
        self.fields['comment'].widget.attrs.update(
            {'class': 'comp-mathcontent-text ctask-comment', 'rows': 3}
        )

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
        fields = ('descriptor', 'max_score', 'max_submissions')


class ChainForm(forms.ModelForm):
    """Form for creating or editing chains.

    For course-like competitions, the `unlock_minutes` and `close_minutes`
    fields are replaced with `unlock_days` and `close_days` fields.
    """

    class Meta:
        model = Chain
        fields = [
            'name',
            'category',
            'position',
            'bonus_score',
            'unlock_mode',
            # Note: `unlock/close_minutes` are replaced with `unlock_close/days`
            # for courses. If changing the order, make sure that `__init__` correctly
            # orders the fields in `self.fields` after these changes are made.
            'unlock_minutes',
            'close_minutes',
            'restricted_access',
        ]

    def __init__(self, *args, **kwargs):
        self.competition = kwargs.pop('competition')
        super(ChainForm, self).__init__(*args, **kwargs)
        if self.competition.is_course:
            instance = self.instance
            restricted_access_field = self.fields.pop('restricted_access')
            self.fields['unlock_days'] = forms.FloatField(
                label=_("Unlock time"),
                min_value=0,
                initial=(instance.unlock_minutes / (24 * 60.0) if instance else 0),
                help_text=self.fields['unlock_minutes'].help_text,
            )
            self.fields['close_days'] = forms.FloatField(
                label=_("Close time"),
                min_value=0,
                initial=(instance.close_minutes / (24 * 60.0) if instance else 0),
                help_text=self.fields['close_minutes'].help_text,
            )
            del self.fields['unlock_minutes']
            del self.fields['close_minutes']
            # Reinsert the restricted_access field to put it at the end.
            self.fields['restricted_access'] = restricted_access_field

    def clean(self):
        data = self.cleaned_data
        if self.competition.is_course:
            try:
                data['close_minutes'] = int((data['close_days'] or 0) * 24 * 60)
            except KeyError:
                raise forms.ValidationError("close_days missing")

            try:
                data['unlock_minutes'] = int((data['unlock_days'] or 0) * 24 * 60)
            except KeyError:
                raise forms.ValidationError("unlock_days missing")

            del data['close_days']
            del data['unlock_days']
        return data


def clean_unused_ctask_ids(competition, ctask_ids):
    if not ctask_ids:
        return [], []
    try:
        ctask_ids = [int(x) for x in ctask_ids.split(',')]
    except ValueError:
        raise ValidationError("Invalid input.")
    ctasks_dict = CompetitionTask.objects.filter(competition=competition).in_bulk(
        ctask_ids
    )
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

        def configure_field(
            field_name, class_=None, help_to_label=False, help_text=None
        ):
            field = self.fields[field_name]
            if class_:
                field.widget.attrs.update({'class': class_})
            if help_to_label:
                field.label = mark_safe(
                    u'{} <i class="icon-question-sign" title="{}"></i>'.format(
                        field.label, xss.escape(unicode(field.help_text))
                    )
                )
                field.help_text = ""
            if help_text:
                field.help_text = help_text

        configure_field('name', 'span6')
        configure_field('category', 'span6')
        configure_field('position', 'span1')
        configure_field('bonus_score', 'span1')
        configure_field('unlock_mode', None, True)
        if 'unlock_minutes' in self.fields:
            configure_field('unlock_minutes', 'span1', True, _("[minutes]"))
            configure_field('close_minutes', 'span1', True, _("[minutes]"))
            self.fields['unlock_minutes'].label = _("Unlock time")
            self.fields['close_minutes'].label = _("Close time")
        else:
            configure_field('unlock_days', 'span1', True, _("[days]"))
            configure_field('close_days', 'span1', True, _("[days]"))
        configure_field('restricted_access', None, True)
        self.fields['ctask_ids'].widget.attrs.update({'id': 'cchain-unused-ctasks-ids'})

    def clean_ctask_ids(self):
        ctask_ids, ctasks = clean_unused_ctask_ids(
            self.competition, self.cleaned_data['ctask_ids']
        )
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
        self.competition = kwargs.pop('competition')
        self.user = kwargs.pop('user')

        if instance:
            # The author cannot be removed from the team.
            team_members = list(
                TeamMember.objects.filter(team=instance)
                .exclude(member_id=instance.author_id)
                .values_list('member_name', 'member_id')
            )
        else:
            team_members = []

        # Add extra fields for other members.
        for k in range(2, self.competition.max_team_size + 1):
            if k - 2 < len(team_members):
                member_name = team_members[k - 2]
            else:
                member_name = ''
            field_manual = 'member{}_manual'.format(k)
            field_username = 'member{}_username'.format(k)
            initial[field_manual] = member_name
            initial[field_username] = member_name

            # Label empty because the HTML is generated via JavaScript anyway.
            extra_fields.append(
                (field_manual, forms.CharField(required=False, label="", max_length=64))
            )
            extra_fields.append(
                (
                    field_username,
                    forms.CharField(
                        required=False, max_length=32, widget=forms.HiddenInput()
                    ),
                )
            )

        # Parse the team category string.
        self.categories = self.competition.parse_team_categories()
        if self.categories:
            try:
                category_choices = self.categories.as_choices(lang)
            except KeyError:
                category_choices = [
                    (
                        1,
                        u"team_categories empty or not available for the current language",
                    )
                ]
            if not category_choices:
                category_choices = [(0, u"team_categories empty!!!")]
        else:
            category_choices = [(0, u"team_categories invalid!!!")]
        self.category_choices = category_choices

        super(TeamForm, self).__init__(initial=initial, *args, **kwargs)

        # Preserve order.
        for key, value in extra_fields:
            self.fields[key] = value

        if self.competition.are_team_names_configurable:
            self.fields['name'].label = ""
            self.fields['name'].widget.attrs['class'] = 'input-large'
            self.fields['name'].error_messages['required'] = _(
                "Please enter the team name."
            )
        else:
            del self.fields['name']

        if self.categories.configurable:
            self.fields['category'].widget = forms.RadioSelect(
                choices=category_choices, renderer=TeamCategoryRadioSelectRenderer
            )
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
                raise ValidationError(_("You are automatically added to the team."))
            if (
                TeamMember.objects.filter(
                    team__competition_id=self.competition.id,
                    member_id=user.id,
                    invitation_status=TeamMember.INVITATION_ACCEPTED,
                )
                .exclude(team_id=self.instance.id)
                .exists()
            ):
                msg = _("User \"%s\" is already a member of a team.") % username
                raise ValidationError(msg)
            return (user.username, user)
        if manual and manual.strip():
            return (manual.strip(), None)
        return (None, None)

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if (
            Team.objects.filter(competition_id=self.competition.id, name__iexact=name)
            .exclude(id=self.instance.id)
            .exists()
        ):
            raise ValidationError(_("Team name already used!"))
        return name

    def clean_category(self):
        category = self.cleaned_data['category']

        if all(category != key for key, value in self.category_choices):
            raise ValidationError(_("Unknown team category '%s'!") % category)

        return category

    def clean(self):
        other_members = []
        ids = set()
        for k in range(2, self.competition.max_team_size + 1):
            member_name, member_user = self._clean_member(k)
            if not member_name:
                continue
            if isinstance(member_user, User):
                if member_user.id not in ids:
                    ids.add(member_user.id)
                    other_members.append((member_name, member_user))
            else:
                other_members.append((member_name, member_user))

        self.other_members = other_members

        if not self.competition.are_team_names_configurable:
            self.cleaned_data['name'] = self.user.username

        return self.cleaned_data

    def save(self, *args, **kwargs):
        """Automatically set the competition and the author."""
        commit = kwargs.pop('commit', True)
        instance = super(TeamForm, self).save(*args, commit=False, **kwargs)
        if instance:
            if not instance.competition_id:
                instance.competition = self.competition
            if not instance.author_id:
                instance.author = self.user
            if commit:
                instance.save()
        return instance

    class Meta:
        model = Team
        fields = ['name', 'category']


class TaskListAdminPanelForm(forms.Form):
    filter_by_team_type = forms.ChoiceField(
        [
            (Team.TYPE_NORMAL, ugettext_lazy("Competitors")),
            (Team.TYPE_UNOFFICIAL, ugettext_lazy("Unofficial")),
            (Team.TYPE_ADMIN_PRIVATE, ugettext_lazy("Administrators")),
        ]
    )
    filter_by_status = forms.ChoiceField(
        [('S', "Solved"), ('F', "Failed"), ('T', "Tried")]
    )
