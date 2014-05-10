from django.conf.urls.defaults import patterns, include, url
from django.contrib.auth.models import User
from django.views.generic import DetailView, ListView, TemplateView

from userprofile.forms import AuthenticationFormEx

urlpatterns = patterns('',
    (r'^memberlist/$', 'userprofile.views.member_list'),

    (r'^profile/(?P<pk>\d+)/', 'userprofile.views.profile'),
    (r'^profile/edit/', 'userprofile.views.edit'),

    (r'^accounts/login/$', 'django.contrib.auth.views.login', {
        'template_name': 'registration/login.html',
        'authentication_form': AuthenticationFormEx}),
    (r'^accounts/logout/$', 'userprofile.views.logout'),
    url(r'^accounts/register/$', 'userprofile.views.new_register',
        name='registration_register'),
    (r'^accounts/', include('registration.backends.default.urls')),
)
