import logging

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group, User
from django.utils.safestring import mark_safe
from django.utils.translation import pgettext_lazy
from django.utils.translation import ugettext_lazy as _

from skoljka.rating.widgets import RatingWidget
from skoljka.task.models import DIFFICULTY_RATING_ATTRS
from skoljka.userprofile.challenge import (
    Challenge,
    InvalidChallengeKey,
    challenge_handler,
)
from skoljka.userprofile.models import UserProfile
from skoljka.utils.testutils import IS_TESTDB
from skoljka.utils.widgets import NonStickyTextInput

if IS_TESTDB:
    from skoljka.userprofile.challenge import test_challenge_handler

# TODO: Upgrado to Django 1.5 (merge UserProfile with User)

logger = logging.getLogger('skoljka.registration')


class AuthenticationFormEx(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(AuthenticationFormEx, self).__init__(*args, **kwargs)

        self.fields['username'].widget.attrs['placeholder'] = _("Username")
        self.fields['password'].widget.attrs['placeholder'] = _("Password")
        for x in self.fields.itervalues():
            x.label = ''
            x.widget.attrs['class'] = 'input-large'


# na temelju django-registration/forms.py RegistrationForm

attrs_dict = {'class': 'required'}
CHALLENGE_KEY = 'ck'
CHALLENGE_ANSWER = 'ca'


class UserCreationForm(forms.Form):
    username = forms.RegexField(
        regex=r'^\w+$',
        max_length=30,
        widget=forms.TextInput(attrs=attrs_dict),
        label=_(u"Username"),
    )
    email = forms.EmailField(
        widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=75)), label=_(u"Email")
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs=attrs_dict, render_value=False),
        label=_(u"Password"),
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs=attrs_dict, render_value=False),
        label=_(u"Confirm password"),
    )
    # Obfuscate names.
    ck = forms.CharField(required=True, widget=forms.HiddenInput())
    ca = forms.CharField(
        required=True,
        label=pgettext_lazy(u"registration challenge", u"Answer"),
        widget=NonStickyTextInput(),
    )
    tou = forms.BooleanField(
        required=True,
        label=_(u'I accept the <a href="/tou/">Terms of Use</a>'),
        error_messages={
            'required': _(
                u"You may not use Školjka if you do not accept the Terms of Use."
            )
        },
    )

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request')
        if IS_TESTDB and 'test_registration_challenge' in request.GET:
            self.challenge_handler = test_challenge_handler
            new_challenge = Challenge(
                index=int(request.GET['test_registration_challenge'])
            )
        else:
            self.challenge_handler = challenge_handler
            new_challenge = challenge_handler.create_random()
        initial = kwargs.pop('initial', {})
        initial[CHALLENGE_KEY] = self.challenge_handler.to_key(new_challenge)

        super(UserCreationForm, self).__init__(*args, initial=initial, **kwargs)

        self.new_challenge = new_challenge
        self.challenge_img = mark_safe(self.challenge_handler.to_html(new_challenge))

        for x in self.fields.itervalues():
            if not isinstance(x, forms.CharField):
                # Terms of Use has a link.
                x.label = mark_safe(x.label)
                continue
            # Show the label as a placeholder.
            x.widget.attrs['placeholder'] = x.label
            x.label = ""
            x.widget.attrs['class'] = x.widget.attrs.get('class', '') + ' input-large'

        self.fields[CHALLENGE_ANSWER].widget.attrs['class'] += ' reg-ch-input'

    def clean_username(self):
        username = self.cleaned_data['username']
        if (
            User.objects.filter(username__iexact=username).exists()
            or Group.objects.filter(name__iexact=username).exists()
        ):
            raise forms.ValidationError(
                _(u"This name is already reserved. Please choose another.")
            )
        return self.cleaned_data['username']

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_(u"E-mail address already in use."))
        return self.cleaned_data['email']

    def clean_ca(self):
        """Clean challenge answer."""
        if CHALLENGE_KEY not in self.cleaned_data:
            logger.warn("Challenge info missing.")
            raise forms.ValidationError(u"Broken form.")  # Bad request.
        try:
            challenge = self.challenge_handler.from_key(
                self.cleaned_data[CHALLENGE_KEY]
            )
        except InvalidChallengeKey:
            logger.warn("Bad challenge key.")
            raise forms.ValidationError(u"Bad input.")

        if not self.challenge_handler.is_answer_correct(
            challenge, self.cleaned_data[CHALLENGE_ANSWER].strip()
        ):
            logger.info("Incorrect answer for index={}.".format(challenge.index))
            raise forms.ValidationError(_(u"Incorrect answer, please try again."))
        else:
            logger.info("Correct answer for index={}.".format(challenge.index))

        return self.cleaned_data[CHALLENGE_ANSWER]

    def clean(self):
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError(_(u"Passwords do not match!"))
        return self.cleaned_data


class UserEditForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)

        self.fields['first_name'].label = 'Ime'
        self.fields['last_name'].label = 'Prezime'

    class Meta:
        model = User
        fields = ['first_name', 'last_name']


class UserProfileEditForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(UserProfileEditForm, self).__init__(*args, **kwargs)

        # self.fields['gender'].widget.attrs['class'] = 'span2'
        self.fields['hide_solution_min_diff'].required = False
        self.fields['hide_solution_min_diff'].widget = RatingWidget(
            attrs=DIFFICULTY_RATING_ATTRS
        )

    def clean_hide_solution_min_diff(self):
        data = self.cleaned_data['hide_solution_min_diff']

        if not data:
            data = 0
        return data

    class Meta:
        model = UserProfile
        fields = [
            'gender',
            'school_class',
            'show_hidden_tags',
            'show_unsolved_task_solutions',
            'hide_solution_min_diff',
            'evaluator',
        ]
