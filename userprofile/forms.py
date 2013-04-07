from django import forms
from django.contrib.admin import widgets
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User, Group
from django.utils.translation import ugettext_lazy as _

from rating.widgets import RatingWidget
from task.models import DIFFICULTY_RATING_ATTRS

from userprofile.models import UserProfile

from registration.models import RegistrationProfile

# TODO: Upgrado to Django 1.5 (merge UserProfile with User)

class AuthenticationFormEx(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(AuthenticationFormEx, self).__init__(*args, **kwargs)
        self.fields['username'].label = 'Korisničko ime'
        self.fields['username'].widget.attrs['autofocus'] = 'autofocus'
        self.fields['password'].label = 'Lozinka'


# na temelju django-registration/forms.py RegistrationForm

attrs_dict = {'class': 'required'}

class UserCreationForm(forms.Form):
    username = forms.RegexField(regex=r'^\w+$', max_length=30, widget=forms.TextInput(attrs=attrs_dict), label=_(u'Korisničko ime'),
        help_text=_(u'Molimo koristite oblik <i>iprezime</i> ili <i>imeprezime</i>.'))
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=75)), label=_(u'Email'))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict, render_value=False), label=_(u'Lozinka'))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict, render_value=False), label=_(u'Lozinka (ponovno)'))

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exists() \
            or Group.objects.filter(name__iexact=username).exists():
            raise forms.ValidationError(_(u'This name is already reserved. Please choose another.'))
        return self.cleaned_data['username']

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_(u'E-mail address already in use. Please choose another.'))
        return self.cleaned_data['email']

    def clean(self):
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError(_(u'You must type the same password each time'))
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

        self.fields['gender'].widget.attrs['class'] = 'span2'
        self.fields['hide_solution_min_diff'].required = False
        self.fields['hide_solution_min_diff'].widget = \
            RatingWidget(attrs=DIFFICULTY_RATING_ATTRS)

    def clean_hide_solution_min_diff(self):
        data = self.cleaned_data['hide_solution_min_diff']

        if not data:
            data = 0
        print 'ovdje asfadf', self, data
        return data

    class Meta:
        model = UserProfile
        fields = ['gender', 'show_hidden_tags', 'show_unsolved_task_solutions',
            'hide_solution_min_diff', 'show_solution_task', 'evaluator']
