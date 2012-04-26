from django.conf.urls.defaults import patterns, include, url
from django.views.generic import DetailView, ListView, TemplateView

from django.contrib.auth.models import User

urlpatterns = patterns('',
# TODO: move to admin
    (r'^refreshscore/$', 'userprofile.views.refresh_score'),

    (r'^memberlist/$', ListView.as_view(
        queryset=User.objects.select_related('profile').exclude(username='arhiva'),
        context_object_name="user_list",
        template_name="memberlist.html",
    )),
    
    (r'^ranks/$', ListView.as_view(
        queryset=User.objects.select_related('profile').order_by('-profile__score', '-profile__solved_count'),
        context_object_name='users',
        template_name='ranks.html')),

    (r'^profile/(?P<pk>\d+)/', 'userprofile.views.profile'),
    (r'^profile/edit/', 'userprofile.views.edit'),
    (r'^register/$', 'userprofile.views.register'),
    (r'^register/complete/', TemplateView.as_view(template_name='registration_complete.html')),
    (r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    (r'^logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'}),

    url(r'^accounts/register/$', 'userprofile.views.new_register', name='registration_register'),
    (r'^accounts/', include('registration.urls')),
)
