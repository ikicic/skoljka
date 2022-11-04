from django.conf.urls.defaults import patterns, include, url
from django.contrib.auth.models import User
from django.views.generic import DetailView, ListView, TemplateView

from skoljka.userprofile.forms import AuthenticationFormEx
import skoljka.userprofile.views as views

urlpatterns = patterns('',
    (r'^memberlist/$', views.member_list),

    (r'^profile/(?P<pk>\d+)/', views.profile),
    (r'^profile/edit/', views.edit),

    (r'^accounts/login/$', 'django.contrib.auth.views.login', {
        'template_name': 'registration/login.html',
        'authentication_form': AuthenticationFormEx}),
    (r'^accounts/logout/$', views.logout),
    url(r'^accounts/activate/complete/$',
        views.activation_complete,
        name='registration_complete'),
    url(r'^accounts/register/$',
        views.new_register,
        name='registration_register'),
    url(r'^accounts/register/complete/$',
        views.registration_complete,
        name='registration_complete'),
    (r'^accounts/', include('registration.backends.default.urls')),
)